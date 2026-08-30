# SPDX-License-Identifier: MIT
# @author Syed Syed 

import logging
from cocotb.triggers import Event, Timer, First
from .memory import Memory
from .defs import *
import uuid

class NvmeQueue():
    def __init__(self, size=None, qid=None, baseaddr=None, mapped_qid=None, ien=0, iv=0):
        self.size = size
        self.qid = qid
        self.dbell = 0
        self.head = 0
        self.tail = 0
        #ctrlr starts with ptag = 1
        self.ptag = 1
        self.base_addr = baseaddr
        self.mapped_qid = mapped_qid
        self.ien = ien
        self.iv = iv
        # sq process thread id
        self.tid = None

class NvmeNs(Memory):
    def __init__(self, nsid=1):
        lbas = 512
        num_lbas = 1024 * 1024
        total_sz = lbas * num_lbas
        super().__init__(size=total_sz)

        self.log = logging.getLogger("cocotb.nvme.ns")

        self.size = total_sz #default to 512MB
        self.capacity = total_sz
        self.lbas = lbas
        self.nuse = total_sz
        self.nsid = nsid
        #self.uuid = uuid.uuid4().hex
        # nguid from nguid.com
        # self.nguid = b"\xFA\x3F\xCF\xDF\xB4\xC5\x4B\x61\x8B\x79\x86\xAF\xB4\x8F\xD7\xFD"
        self.eui64 = b"\xc0\xc0\x00\x00\x12\x34\x56\x78"

    def read_blocks(self, start, nblocks):
        addr = start * self.lbas
        length = nblocks * self.lbas
        self.log.debug("read_blocks: len: %r size rem:%r addr: %r", length, self.size - addr, addr)
        if(length > (self.size - addr)):
            self.log.warning("Boundary Error: Read from NS, MAX SIZE:",self.size);
        return self.read(addr, length)

    def write_blocks(self, start, data):
        addr = start * self.lbas
        if(len(data) > (self.size - addr)):
            self.log.warning("Boundary Error: Write to NS, MAX SIZE:",self.size);

        return self.write(addr, data)


class NvmeController():
    def __init__(self, ep):

        self.ep = ep 

        self.log = logging.getLogger("cocotb.nvme.controller")

        self.mps = 0x1000

        #nvme queues
        self.submission_queues = []
        self.completion_queues = []

        self.admin_tid = None

        # io processing threads
        self.io_threads = []

        self.identify_ctrl = identify_ctrlr()
        self.identify_ctrl.cntlid.integer = 1
        self.ep.identify_ctrl = self.identify_ctrl

        self.sec_ctrl_list = NvmeSecCtrlList()

        #Define controller conf
        self.cc = nvme_cc()
        self.csts = nvme_csts()

        # namespaces
        self.active_ns = []

        ns = NvmeNs(nsid=1)
        self.active_ns.append(ns)

        admin_sq = NvmeQueue(qid=0, mapped_qid=0)
        self.submission_queues.append(admin_sq)

        admin_cq = NvmeQueue(qid=0, mapped_qid=0)
        self.completion_queues.append(admin_cq)

        self.ep.register_nvme_write_handler(self.ctrlr_write_handler)

    def ctrlr_get_cq(self, qid):
        for cq in self.completion_queues:
            if cq.qid == qid:
                return cq
        return None

    def ctrlr_get_sq(self, qid):
        for sq in self.submission_queues:
            if sq.qid == qid:
                return sq
        return None

    async def ctrlr_raise_intr(self, cq):
        # raise msi interrupt
        intr_base = self.ep.msi_cap.msix_table_offset
        if(cq.ien == True):
            intr_base += (cq.iv * 16)
        self.log.debug("INT BASE: %r", intr_base)
        addr = await self.ep.read_region(1, intr_base, 4)
        msi_addr = int.from_bytes(addr, byteorder="little")
        msi_data = await self.ep.read_region(1, intr_base + 8, 4)
        self.log.debug("msix host addr %r MSI DATA: %r", hex(msi_addr), msi_data)
        await self.ep.mem_region.write(msi_addr, msi_data)
        return

    async def ctrlr_write_handler(self, off, data, func):
        self.log.info("ctrlr_write_handler: off: %r", hex(off))
        if (off == 0x14):
            vec = BinaryValue(n_bits=32, bigEndian=True)
            cc = self.cc
            vec.assign(data[::-1]) # we read data in little endian
            cc.populate(vec)
            self.log.debug("cc.en: %r", cc.en.integer)
            self.log.debug("cc.iocqes: %r", cc.iocqes.integer)
            self.log.debug("cc.mps: %r", cc.mps.integer)
            # TODO check mps against mpsmin, mpsmax
            if (cc.en.integer == 0):
                await self.ctrlr_reset()
                return

            if (cc.en.integer == 1):
                await self.ctrlr_enable()
                return

        # CQ Doorbell
        # assuming dstrd = 0
        if (off > 0x1000 and (off & 0x4 == 0x4)):
            data = await self.ep.read_region(0, off, 4)
            doorbell = int.from_bytes(data, "little")
            self.log.debug("cq doorbell : %r", doorbell)
            cqid = (((off - 0x1000) >> 2) - 1) >> 1
            self.log.debug("cq id:%r", cqid)
            cq = self.ctrlr_get_cq(cqid)
            cq.head = doorbell
            if (cq.head != cq.tail):
                await self.ctrlr_raise_intr(cq)

        if (off == 0x24): # AQA
            vec = BinaryValue(n_bits=32, bigEndian=True)
            aqa = nvme_aqa()
            vec.assign(data[::-1])
            aqa.populate(vec)
            queue = self.submission_queues[0]
            queue.size = aqa.asqs.integer + 1 # 0 base value
            self.log.debug("ASQ Size:%r", queue.size)
            queue = self.completion_queues[0]
            queue.size = aqa.acqs.integer + 1
            self.log.debug("ACQ Size:%r", queue.size)
            return

        if (off == 0x2c): # ASQ
            data = await self.ep.read_region(0, 0x28, 8)
            vec = BinaryValue(n_bits=64, bigEndian=True)
            asq = nvme_asq()
            vec.assign(data[::-1])
            asq.populate(vec)
            sq = self.submission_queues[0]
            # we get 52 msb of asqb, shift by 12 to get 64bit addr
            sq.base_addr = (asq.asqb.integer << 12)
            self.log.debug("asq.integer: %r", hex(asq.asqb.integer))
            self.log.debug("sq base: %r", hex(sq.base_addr))
            return

        if (off == 0x34): # ACQ
            data = await self.ep.read_region(0, 0x30, 8)
            vec = BinaryValue(n_bits=64, bigEndian=True)
            acq = nvme_acq()
            vec.assign(data[::-1])
            acq.populate(vec)
            cq = self.completion_queues[0]
            # we get 52 msb of asqb, shift by 12 to get 64bit addr
            cq.base_addr = (acq.acqb.integer << 12)
            self.log.debug("cq base: %r", hex(cq.base_addr))
            return
        



    async def ctrlr_enable(self):
        self.log.info("enabling the controller")
        csts = self.csts
        csts.ready.integer = 1
        await self.ep.write_region(0, 0x1c, csts.to_bus(bigEndian=False).buff)
        self.admin_tid = cocotb.start_soon(self.ctrlr_admin_sq_process())

    async def ctrlr_reset(self):
        self.log.info("resetting the controller")
        if (self.admin_tid is not None):
            self.admin_tid.kill()
            self.admin_tid = None

        for tid in self.io_threads:
            tid.kill()
            self.io_threads.remove(tid)

        # delete all I/O SQs and CQs
        for sq in self.submission_queues:
            if sq.qid != 0:
                self.submission_queues.remove(sq)

        for cq in self.completion_queues:
            if cq.qid != 0:
                self.completion_queues.remove(cq)

        # reset admin sq
        sq = self.submission_queues[0]
        sq.head = 0
        sq.tail = 0
        sq.dbell = 0

        # reset admin cq
        cq = self.completion_queues[0]
        sq.ptag = 1
        cq.head = 0
        cq.tail = 0
        cq.dbell = 0

        caps = nvme_caps()

        caps.mpsmax.integer = 0 # 4096
        caps.mpsmin.integer = 0

        caps.css.integer = 1 # nvm command set
        caps.nssrs.integer = 1 # nvm subsystem reset supported
        caps.timeout.integer = 6
        caps.dstrd.integer = 0
        caps.mqes.integer = 0xfff #4k
        caps.cqr.integer = 1

        await self.ep.write_region(0, 0x0, caps.to_bus(bigEndian=False).buff)
        #reset asq doorbell
        await self.ep.write_region(0, 0x1000, b'\x00\x00\x00\x00')

        csts = self.csts
        csts.ready.integer = 0
        await self.ep.write_region(0, 0x1c, csts.to_bus(bigEndian=False).buff)

    async def ctrlr_admin_sq_process(self):
        sq = self.submission_queues[0]
        while True:
            data = await self.ep.read_region(0, 0x1000, 4)
            doorbell = int.from_bytes(data, "little")
            #print ("new doorbell: ", doorbell)
            while (sq.head != doorbell):
                sq_addr = sq.base_addr + (sq.head) * (64)
                data = await self.ep.mem_region.read(sq_addr, 64)
                #print ("cmd data: ", data)
                cmd = nvme_cmd()
                vec = BinaryValue(n_bits=512, bigEndian=True)
                vec.assign(data[::-1])
                cmd.populate(vec)

                if (cmd.opc.integer == AdminCmd.Identify):
                    await self.ctrlr_cmd_identify(cmd)
                elif (cmd.opc.integer == AdminCmd.CreateIoCq):
                    await self.ctrlr_cmd_createiocq(cmd)
                elif (cmd.opc.integer == AdminCmd.CreateIoSq):
                    await self.ctrlr_cmd_createiosq(cmd)
                elif (cmd.opc.integer == AdminCmd.GetLogPage):
                    await self.ctrlr_cmd_getlogpage(cmd)
                elif (cmd.opc.integer == AdminCmd.DeleteIoSq):
                    await self.ctrlr_cmd_deleteiosq(cmd)
                elif (cmd.opc.integer == AdminCmd.DeleteIoCq):
                    await self.ctrlr_cmd_deleteiocq(cmd)
                elif (cmd.opc.integer == AdminCmd.SetFeatures):
                    await self.ctrlr_cmd_setfeatures(cmd)
                else:
                    self.log.warning("Unhandled admin cmd: ", cmd.opc.integer)
                    raise Exception("Unhandled admin cmd: ", cmd.opc.integer)


                #print ("sq.head: ", sq.head)
                #print ("doorbell: ", doorbell)
                # increment sq head
                sq.head = (sq.head + 1) % (sq.size)
                self.log.debug("After increment sq.head :%r ", sq.head)
            await Timer(10000, units="ns")

    async def ctrlr_write_completion(self, sq, cmd, dw0=0, sct=0, sc=0):
        cq = self.completion_queues[sq.mapped_qid]

        if(cq.size==0):
            self.log.debug("Not a valid CQ")
            return
        cpl = nvme_cpl()
        cpl.cmdspec.integer = dw0
        cpl.sqid.integer = sq.qid
        cpl.sqhd.integer = sq.head
        cpl.cid.integer = cmd.cid.integer
        cpl.ptag.integer = cq.ptag
        cpl.sc.integer = 0
        cpl.sct.integer = 0
        dest = cq.base_addr + (cq.tail * (cpl.bus_len()//8))
        # write the completion
        #print ("writing completion at", hex(dest), "for cmd-id:", cmd.cid.integer)
        data = cpl.to_bus(bigEndian=False).buff
        await self.ep.mem_region.write(dest, data)

        if (cq.tail + 1 == cq.size): # wrap around?
            cq.ptag = cq.ptag ^ 1

        # increment head
        cq.tail = (cq.tail + 1) % (cq.size)
        if (cq.head != cq.tail):
            await self.ctrlr_raise_intr(cq)

    async def read_dma_data(self, prp1, prp2, data_len):
        offset = prp1 % self.mps
        dma_data = bytearray()
        if(data_len <= self.mps):
            self.log.debug("DMA DATA <= %r",self.mps)
            if (offset == 0): # PRP1 is an entry with 4k aligned
                data = await self.ep.mem_region.read(prp1, data_len)
                dma_data.extend(data)
            else:
                size = (self.mps - offset)
                data = await self.ep.mem_region.read(prp1, size)
                dma_data.extend(data)
                data = await self.ep.mem_region.read(prp2, offset)
                dma_data.extend(data)
        else:
            self.log.debug("DMA DATA > %r",self.mps)
            size = self.mps - offset
            data = await self.ep.mem_region.read(prp1, size)
            dma_data.extend(data)
            data_len -= size
            prp_list = False
            while(data_len > self.mps):
                add = await self.ep.mem_region.read(prp2, 8)
                add = int.from_bytes(add, byteorder="little")
                data = await self.ep.mem_region.read(add, self.mps)
                dma_data.extend(data)
                size += self.mps
                prp2 += 8
                data_len -= self.mps
                prp_list = True
            if(data_len > 0):
                self.log.debug("DMA DATA > 0 and < %r",self.mps)
                if(prp_list == True):
                    add = await self.ep.mem_region.read(prp2, 8)
                    add = int.from_bytes(add, byteorder="little")
                    data = await self.ep.mem_region.read(add, data_len)
                    dma_data.extend(data)
                    size += data_len
                else:
                    data = await self.ep.mem_region.read(prp2, data_len)
                    dma_data.extend(data)
                    size += data_len
        return dma_data


    async def ctrlr_write_resp(self, prp1, prp2, data):
        offset = prp1 % self.mps
        data_len = len(data)
        if(data_len <= self.mps):
            self.log.debug("DMA DATA <= 4096")
            if (offset == 0): # PRP1 is an entry with 4k aligned
                await self.ep.mem_region.write(prp1, data, self.mps)
            else:
                size = (self.mps - offset)
                await self.ep.mem_region.write(prp1, data[0:size-1], size)
                await self.ep.mem_region.write(prp2, data[size:-1], offset)
        else:
            size = self.mps - offset
            await self.ep.mem_region.write(prp1, data[0:size-1], size)
            data_len -= size
            prp_list = False
            while(data_len > self.mps):
                add = await self.ep.mem_region.read(prp2, 8)
                add = int.from_bytes(add, byteorder="little")
                dma_size = size + self.mps
                await self.ep.mem_region.write(add, data[size:dma_size-1], self.mps)
                size = dma_size
                prp2 += 8
                data_len -= self.mps
                prp_list = True
            if(data_len > 0):
                if(prp_list == True):
                    add = await self.ep.mem_region.read(prp2, 8)
                    add = int.from_bytes(add, byteorder="little")
                    await self.ep.mem_region.write(add, data[size:-1], self.mps)
                else:
                    await self.ep.mem_region.write(prp2, data[size:-1], offset)

    async def ctrlr_write_data(self, prp1, prp2, data):
        self.log.info("ctrlr_write_data: len: ", len(data))
        offset = prp1 % self.mps
        if (offset == 0): # prp is an entry
            await self.ep.mem_region.write(prp1, data, len(data))
        else:
            length = len(data)
            size = (length - offset)
            await self.ep.mem_region.write(prp1, data[0:size-1], size)

    async def ctrlr_read_data(self, prp1, prp2, length):
        offset = prp1 % self.mps
        if (offset == 0): #PRP is an entry
            data = await self.ep.mem_region.read(prp1, length)
        else:
            size = (4096 - offset)
            data = await self.ep.mem_region.read(prp1, size)
        return data

    async def ctrlr_cmd_identify(self, cmd):
        self.log.info("CMD : Identify")
        prp1 = cmd.prp1.integer
        prp2 = cmd.prp2.integer

        cdw10 = id_cdw10()
        cdw10.populate(cmd.dw10)
        status_code = 0
        if (cdw10.cns.integer == Cns.IdCtrlr): # identify controller
            self.log.info("Identify controller: ")
            identify = self.identify_ctrl
            identify.vid.integer = self.ep.vendor_id
            identify.ssid.integer = self.ep.device_id
            identify.sn.buff = b"COSIM00000000000001 "
            identify.mn.buff = b"cocotbext-nvme controller" + b" " * 15
            identify.fr.buff = b"1.0     "
            version = nvme_version()
            version.mjr.integer = 1
            version.mnr.integer = 4
            version.ter.integer = 0
            identify.ver = version.to_bus(bigEndian=False)
            # sq entry size = 6 or 64 bytes
            identify.sqes.integer = (6 << 4) | 6
            # cq entry size = 6 or 64 bytes
            identify.cqes.integer = (6 << 4) | 6
            # can process 4 cmds at a time
            identify.maxcmd.integer = 4
            identify.nn.integer = 1 #only support 1 namespace
            identify.avscc.integer = 1
            identify.tnvmcap0.integer = 2**32
            identify.unvmcap0.integer = 0
            nqn = str(b'nqn.2023-10.io.amd:cocotb1')
            identify.subnqn.integer = int.from_bytes(nqn.encode('utf-8'), "big")
            # formatnvm supported
            identify.oacs.integer = (1<<1)
            # write the response to dest
            data = identify.to_bus(bigEndian=False).buff
            await self.ctrlr_write_resp(prp1, prp2, data)
        elif (cdw10.cns.integer == Cns.IdNsp): #identify namespace
            identify = identify_namespace()
            self.log.info("Identify namespace nsid: ", cmd.nsid.integer)
            if (cmd.nsid.integer == 1):
                lbaf = id_lbaf()
                ns = self.active_ns[0]
                identify.nsze.integer = (ns.size//ns.lbas)
                identify.ncap.integer = (ns.capacity//ns.lbas)
                identify.nuse.integer = (ns.nuse//ns.lbas)
                identify.nsfeat.integer = (1 << 3)
                identify.nlbaf.integer = 1
                identify.flbas.integer = 0 #512 block size
                identify.mc.integer = 0
                identify.dpc.integer = 0
                identify.dps.integer = 0
                #identify.nguid.buff = ns.nguid
                identify.eui64.buff = ns.eui64

                lbaf.ms.integer = 0
                # 512bytes block size
                lbaf.lbads.integer = 9
                data = lbaf.to_bus().buff
                identify.lbaf0.buff = data[::-1]

                # 4096bytes block size
                lbaf.lbads.integer = 12
                data = lbaf.to_bus().buff
                identify.lbaf1.buff = data[::-1]
            else:
                # send zero filled in struct
                pass

            # write the response to dest
            data = identify.to_bus(bigEndian=False).buff
            await self.ctrlr_write_resp(prp1, prp2, data)

        elif (cdw10.cns.integer == Cns.ActiveNsidLst): #active nsid list
            self.log.info("ActiveNsidLst")
            data = bytearray(4096)
            # fill in nsid = 1
            data[0] = 1

            await self.ctrlr_write_resp(prp1, prp2, bytes(data))
            # write the response to dest
            await self.ctrlr_write_resp(prp1, prp2, data)
        elif (cdw10.cns.integer == Cns.ScndCtrlrLst): #active nsid list
            self.log.info("Second controller List Command")
            ctrl_list = self.sec_ctrl_list
            ctrl_list.numctlr.integer = 1
            entry = NvmeSecCtrlEntry()
            entry.scid.integer = 1;
            entry.pcid.integer = 0
            entry.scs.integer = 1
            entry.vfn.integer = 1
            data = bytearray()
            data.extend(ctrl_list.to_bus(bigEndian=False).buff)
            data.extend(entry.to_bus(bigEndian=False).buff)
            await self.ctrlr_write_resp(prp1, prp2, bytes(data))

        else:
            status_code = StatusCode.InvalidField
            self.log.warning("Unhandled cns command: ", cdw10.cns.integer)

        # write the completion
        sq = self.submission_queues[0]
        await self.ctrlr_write_completion(sq, cmd, sc=status_code)

    async def ctrlr_cmd_createiocq(self, cmd):
        self.log.info("CMD : createiocq")
        dw11 = cmd_dw11_createiocq()
        dw10 = cmd_dw10_qinfo()

        dw10.populate(cmd.dw10)
        #print ("create io cq: qsize: ", dw10.qsize.integer)
        self.log.debug("create io cq: qid: %r", dw10.qid.integer)

        dw11.populate(cmd.dw11)
        self.log.debug("create io cq: ien: %r", dw11.ien.integer)
        self.log.debug("create io cq: iv: %r", dw11.iv.integer)
        #print ("create io cq: pc: ", dw11.pc.integer)

        cq = NvmeQueue(qid=dw10.qid.integer,
                        size=dw10.qsize.integer + 1, # zero based vale
                        baseaddr=cmd.prp1.integer,
                        ien=dw11.ien.integer,
                        iv=dw11.iv.integer)
        self.completion_queues.append(cq)

        # write the completion
        await self.ctrlr_write_completion(self.submission_queues[0], cmd)

    async def ctrlr_cmd_createiosq(self, cmd):
        self.log.info("CMD : createiosq")
        dw11 = cmd_dw11_createiosq()
        dw10 = cmd_dw10_qinfo()

        dw10.populate(cmd.dw10)
        dw11.populate(cmd.dw11)

        self.log.debug("Qid : %r", dw10.qid.integer, "qsize: %r",  dw10.qsize.integer)

        sq = NvmeQueue(qid=dw10.qid.integer,
                        size=dw10.qsize.integer + 1, # zero based value
                        baseaddr=cmd.prp1.integer,
                        mapped_qid=dw11.cqid.integer)
        self.submission_queues.append(sq)

        # write the completion
        await self.ctrlr_write_completion(self.submission_queues[0], cmd)
        # start io sq process
        tid = cocotb.start_soon(self.ctrlr_io_sq_process(sq))
        self.io_threads.append(tid)
        sq.tid = tid

    async def ctrlr_cmd_deleteiocq(self, cmd):
        self.log.info("CMD: deleteiocq")
        dw10 = cmd_dw10_qinfo()

        dw10.populate(cmd.dw10)

        self.log.debug("Qid : %r", dw10.qid.integer)
        # write the completion
        await self.ctrlr_write_completion(self.submission_queues[0], cmd)

    async def ctrlr_cmd_deleteiosq(self, cmd):
        self.log.info("CMD: deleteiosq")
        dw10 = cmd_dw10_qinfo()

        dw10.populate(cmd.dw10)

        self.log.debug("Qid : %r", dw10.qid.integer)

        # can't delete ASQ
        if (dw10.qid.integer == 0):
            self.log.warning("Warning: Delete ASQ received. Ignoring")
            return
        # stop the thread
        qid = dw10.qid.integer
        sq = self.ctrlr_get_sq(qid)

        self.io_threads.remove(sq.tid)
        sq.tid.kill()
        sq.tid = None

        # write the completion
        await self.ctrlr_write_completion(self.submission_queues[0], cmd)


    async def ctrlr_cmd_getlogpage(self, cmd):
        self.log.info("CMD : getlogpage")
        dw10 = cmd_dw10_getlogpage()

        dw10.populate(cmd.dw10)

        self.log.info("lid:", dw10.lid.integer)
        lid = dw10.lid.integer

        prp1 = cmd.prp1.integer
        prp2 = cmd.prp2.integer
        self.log.info("prp1 prp2: ", hex(prp1), hex(prp2))

        if (lid == 2): # get smart/health log
            smart_health_log = getlogpage_smart_health()
            smart_health_log.temp_sensor_1.integer = 34 # 34 degrees
            smart_health_log.temp_sensor_2.integer = 96 # 96 degrees
            smart_health_log.avail_spare.integer = 100
            smart_health_log.avail_spare_thres.integer = 12
            data = smart_health_log.to_bus(bigEndian=False).buff
            await self.ctrlr_write_data(prp1, prp2, data)

        # write the completion
        sq = self.submission_queues[0]
        await self.ctrlr_write_completion(sq, cmd)

    async def ctrlr_cmd_setfeatures(self, cmd):
        self.log.info("CMD: setfeatures")

        dw10 = cmd_dw10_setfeature()
        dw10.populate(cmd.dw10)

        self.log.debug("fid :%r", dw10.fid.integer)

        if (dw10.fid.integer == 0x7): # num of queues
            dw11 = cmd_dw11_setfeature()
            dw11.populate(cmd.dw11)
            self.log.debug("nsqr :%r", dw11.nsqr.integer, "ncqr:%r", dw11.ncqr.integer)

        # write the completion
        dw0 = cpl_dw0_numqueues()
        dw0.ncqa.integer = 15
        dw0.nsqa.integer = 15
        val = dw0.to_bus(bigEndian=False).integer
        sq = self.submission_queues[0]
        await self.ctrlr_write_completion(sq, cmd, dw0=val)

    async def ctrlr_cmd_read(self, sq, cmd):
        self.log.info("CMD: Read")
        nsid = cmd.nsid.integer

        slba = (cmd.dw11.integer << 32) | (cmd.dw10.integer)
        self.log.debug("nsid : %r slba: %r", nsid, hex(slba))
        dw12 = read_cdw12()
        dw12.populate(cmd.dw12)
        nlb = dw12.nlb.integer + 1 # zero based value
        self.log.debug("nlb: %r", nlb)

        prp1 = cmd.prp1.integer
        prp2 = cmd.prp2.integer
        self.log.debug("prp1: %r prp2: %r", hex(prp1), hex(prp2))

        ns = self.active_ns[nsid - 1] #NVME Model active_ns starts from 0
        data = ns.read_blocks(slba, nlb)
        self.log.debug("len of data READ op: %r", len(data))
        await self.ctrlr_write_resp(prp1, prp2, data)
        # write the completion
        await self.ctrlr_write_completion(sq, cmd)

    async def ctrlr_cmd_write(self, sq, cmd):
        self.log.info("CMD: Write")
        nsid = cmd.nsid.integer
        slba = (cmd.dw11.integer << 32) | (cmd.dw10.integer)
        self.log.debug("nsid :%r slba:%r ", nsid, hex(slba))
        ns = self.active_ns[nsid - 1]
        dw12 = read_cdw12()
        dw12.populate(cmd.dw12)
        nlb = dw12.nlb.integer + 1 # zero based value
        self.log.debug("nlb: %r", nlb)

        prp1 = cmd.prp1.integer
        prp2 = cmd.prp2.integer

        self.log.debug("prp1 :%r prp2: %r", hex(prp1), hex(prp2))
        data = await self.read_dma_data(prp1, prp2, nlb * ns.lbas)
        self.log.debug("DATA: %r", data)

        ns.write_blocks(slba, data)

        # write the completion
        await self.ctrlr_write_completion(sq, cmd)

    async def ctrlr_io_sq_process(self, sq):
        db_off = 0x1000 + (2 * sq.qid * 4)
        while (True):
            data = await self.ep.read_region(0, db_off, 4)
            doorbell = int.from_bytes(data, "little")
            #print ("ioq :new doorbell: ", doorbell)
            while (sq.head != doorbell):
                sq_addr = sq.base_addr + (sq.head) * (64)
                data = await self.ep.mem_region.read(sq_addr, 64)
                #print ("cmd data: ", data)
                cmd = nvme_cmd()
                vec = BinaryValue(n_bits=512, bigEndian=True)
                vec.assign(data[::-1])
                cmd.populate(vec)
                self.log.debug("CMD :%r", cmd.opc.integer)

                if (cmd.opc.integer == IoCmd.Read):
                    await self.ctrlr_cmd_read(sq, cmd)
                elif (cmd.opc.integer == IoCmd.Write):
                    await self.ctrlr_cmd_write(sq, cmd)
                else:
                    self.log.warning("Unhandled io command: %r", cmd.opc.integer)
                    raise Exception("Unhandled io command: ", cmd.opc.integer)

                #print ("sq.head: ", sq.head)
                sq.head = (sq.head + 1) % (sq.size)
                #print ("After increment sq.head : ", sq.head)
            await Timer(10000, units="ns")


