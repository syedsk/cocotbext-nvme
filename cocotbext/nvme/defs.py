# SPDX-License-Identifier: MIT
# @author Syed Syed 

import enum
from cocotb.binary import BinaryValue
from .bitfield import *

binval = lambda nb: BinaryValue(n_bits=nb, value=0, bigEndian=False)

class AdminCmd(enum.IntEnum):
    DeleteIoSq  = 0x0
    CreateIoSq  = 0x1
    GetLogPage  = 0x2
    DeleteIoCq  = 0x4
    CreateIoCq  = 0x5
    Identify    = 0x6
    Abort       = 0x8
    SetFeatures = 0x9
    GetFeatures = 0xa
    AsyncEventReq = 0xc
    NspMgmt     = 0xd
    FwCommit    = 0x10
    NvmeMISend  = 0x1d
    NvmeMIRecv  = 0x1e


class IoCmd(enum.IntEnum):
    Flush   = 0x0
    Write   = 0x1
    Read    = 0x2
    WriteUncorrectable = 0x4
    Compare = 0x5
    WriteZeroes = 0x8
    DatasetMgmt = 0x9
    Verify      = 0xc
    ResvRegister = 0xd
    ResvReport  = 0xe
    ResvAcquire = 0x11
    ResvRelease = 0x15

class Cns(enum.IntEnum):
    IdNsp        = 0x0
    IdCtrlr      = 0x1
    ActiveNsidLst = 0x2
    NsidDesc     = 0x3
    NvmSetLst    = 0x4
    AllocNsidLst = 0x10
    IdNsidData    = 0x11
    NsidCtrlrLst  = 0x12
    NvmCtrlrLst   = 0x13
    PrimCtrlrCap  = 0x14
    ScndCtrlrLst  = 0x15
    NspGrnlrLst   = 0x16
    UuidLst       = 0x17

class StatusCode(enum.IntEnum):
    Success         = 0x0
    InvalidOpCode   = 0x1
    InvalidField    = 0x2
    CidConflict     = 0x3
    DataXferError   = 0x4
    AbortDueToPower = 0x5
    InternalError   = 0x6
    AbortRequested  = 0x7
    AbortDueToSqDel = 0x8
    AbortDueToFailedFuse    = 0x9
    AbortDueToMissingFuse   = 0xa
    InvalidNs       = 0xb


class nvme_caps(bitfield):
    def __init__(self):
        self.rsvd3  = binval(3)
        self.crms = binval(2)
        self.nsss = binval(1)
        self.cmbs = binval(1)
        self.pmrs = binval(1)
        self.mpsmax  = binval(4)
        self.mpsmin  = binval(4)
        self.rsvd2  = binval(3)
        self.css  = binval(8)
        self.nssrs  = binval(1)
        self.dstrd  = binval(4)
        self.timeout  = binval(8)
        self.rsvd1  = binval(5)
        self.ams  = binval(2)
        self.cqr  = binval(1)
        self.mqes = binval(16)

#version
class nvme_version(bitfield):
    def __init__(self):
        self.mjr = binval(16)
        self.mnr = binval(8)
        self.ter = binval(8)

# controller configuration
class nvme_cc(bitfield):
    def __init__(self):
        self.rsvd2 = binval(8)
        self.iocqes = binval(4)
        self.iosqes = binval(4)
        self.shn = binval(2)
        self.ams = binval(3)
        self.mps = binval(4)
        self.css = binval(3)
        self.rsvd1 = binval(3)
        self.en = binval(1)

# controller status
class nvme_csts(bitfield):
    def __init__(self):
        self.rsvd = binval(28)
        self.shst = binval(2)
        self.cfs = binval(1)
        self.ready = binval(1)

class nvme_aqa(bitfield):
    def __init__(self):
        self.rsvd2 = binval(4)
        self.acqs = binval(12)
        self.rsvd1 = binval(4)
        self.asqs = binval(12)

class nvme_asq(bitfield):
    def __init__(self):
        self.asqb = binval(52)
        self.rsvd = binval(12)

class nvme_acq(bitfield):
    def __init__(self):
        self.acqb = binval(52)
        self.rsvd = binval(12)

class nvme_cmbloc(bitfield):
    def __init__(self):
        self.ofst = binval(20)
        self.rsvd = binval(3)
        self.cqda = binval(1)
        self.cdmms = binval(1)
        self.cdpcils = binval(1)
        self.cdpmls = binval(1)
        self.cqpds = binval(1)
        self.cqmms = binval(1)
        self.bir = binval(3)

class nvme_cmbsz(bitfield):
    def __init__(self):
        self.sz = binval(20)
        self.szu = binval(4)
        self.rsvd = binval(3)
        self.wds = binval(1)
        self.rds = binval(1)
        self.lists = binval(1)
        self.cqs = binval(1)
        self.sqs = binval(1)


class cmd_dw0(bitfield):
    def __init__(self):
        self.cid = binval(16)
        self.psdt = binval(2)
        self.rsvd1 = binval(4)
        self.fuse = binval(2)
        self.opc = binval(8)

class cmd_dw10_qinfo(bitfield):
    def __init__(self):
        self.qsize = binval(16)
        self.qid = binval(16)

class cmd_dw10_getlogpage(bitfield):
    def __init__(self):
        self.numdl = binval(16)
        self.rae = binval(1)
        self.rsvd = binval(3)
        self.lsp = binval(4)
        self.lid = binval(8)

class cmd_dw11_getlogpage(bitfield):
    def __init__(self):
        self.lsid = binval(16)
        self.numdu = binval(16)

class cmd_dw11_createiocq(bitfield):
    def __init__(self):
        self.iv = binval(16)
        self.rsvd1 = binval(14)
        self.ien = binval(1)
        self.pc = binval(1)

class cmd_dw11_createiosq(bitfield):
    def __init__(self):
        self.cqid = binval(16)
        self.rsvd1 = binval(13)
        self.qprio = binval(2)
        self.pc = binval(1)

class cmd_dw10_setfeature(bitfield):
    def __init__(self):
        self.save = binval(1)
        self.rsvd = binval(23)
        self.fid = binval(8)

class cmd_dw11_setfeature(bitfield):
    def __init__(self):
        self.ncqr = binval(16)
        self.nsqr = binval(16)

class nvme_cmd(cmd_dw0):
    def __init__(self):
        self.dw15 = binval(32)
        self.dw14 = binval(32)
        self.dw13 = binval(32)
        self.dw12 = binval(32)
        self.dw11 = binval(32)
        self.dw10 = binval(32)
        self.prp2 = binval(64)
        self.prp1 = binval(64)
        self.mptr = binval(64)
        self.rsvd2 = binval(64)
        self.nsid = binval(32)
        super().__init__()

class cpl_dw0_numqueues(bitfield):
    def __init__(self):
        self.ncqa = binval(16)
        self.nsqa = binval(16)

class nvme_cpl(bitfield):
    def __init__(self):
        self.dnr = binval(1)
        self.m = binval(1)
        self.crd = binval(2)
        self.sct = binval(3)
        self.sc = binval(8)
        self.ptag = binval(1)
        self.cid = binval(16)
        self.sqid = binval(16)
        self.sqhd = binval(16)
        self.rsvd = binval(32)
        self.cmdspec = binval(32)

class read_cdw12(bitfield):
    def __init__(self):
        self.lr  = binval(1)
        self.fua = binval(1)
        self.prinfo = binval(4)
        self.rsvd = binval(10)
        self.nlb = binval(16)

class id_cdw10(bitfield):
    def __init__(self):
        self.cntid = binval(16)
        self.rsvd = binval(8)
        self.cns = binval(8)

class createio_cdw10(bitfield):
    def __init__(self):
        self.qsize = binval(16)
        self.qid = binval(16)
    
class createio_cdw11(bitfield):
    def __init__(self):
        self.cqid = binval(16)
        self.rsvd = binval(13)
        self.qprio = binval(2)
        self.pc = binval(1)

class id_lbaf(bitfield):
    def __init__(self):
        self.rsvd = binval(6)
        self.rp = binval(2)
        self.lbads = binval(8)
        self.ms = binval(16)

class NvmeSecCtrlEntry(bitfield):
    def __init__(self):
       self.rsvf = binval(18*8)
       self.nvi = binval(16) #Number of VI assigned
       self.nvq = binval(16) #NUmber of VQ assigned
       self.vfn = binval(16)
       self.rsvd = binval(8*3)
       self.scs = binval(8) #Secondary controller state
       self.pcid = binval(16) #Primary controller identifier
       self.scid = binval(16) #Secondary list controller identifier

class NvmeSecCtrlList(bitfield):
    def __init__(self):
        self.rsvd = binval(31*8) 
        self.numctlr = binval(8) #Number of identifiers


class getlogpage_smart_health(bitfield):
    def __init__(self):
        self.rsvd2 = binval(280*8)
        self.tot_time_tmt_2 = binval(4*8)
        self.tot_time_tmt_1 = binval(4*8)
        self.tmt_2_trans_count = binval(4*8)
        self.tmt_1_trans_count = binval(4*8)
        self.temp_sensor_8 = binval(16)
        self.temp_sensor_7 = binval(16)
        self.temp_sensor_6 = binval(16)
        self.temp_sensor_5 = binval(16)
        self.temp_sensor_4 = binval(16)
        self.temp_sensor_3 = binval(16)
        self.temp_sensor_2 = binval(16)
        self.temp_sensor_1 = binval(16)
        self.crit_comp_temp_time = binval(4*8)
        self.warn_comp_temp_time = binval(4*8)
        self.num_err_info_log_entries = binval(16*8)
        self.media_data_integrity_errors = binval(16*8)
        self.unsafe_shutdwns = binval(16*8)
        self.pwr_on_hours = binval(16*8)
        self.pwr_cycles = binval(16*8)
        self.ctrlr_busy_time = binval(16*8)
        self.host_write_cmds = binval(16*8)
        self.host_read_cmds = binval(16*8)
        self.data_units_written = binval(16*8)
        self.data_units_read = binval(16*8)
        self.rsvd1 = binval(25*8)
        self.egcws = binval(8) 
        self.percent_used = binval(8)
        self.avail_spare_thres = binval(8)
        self.avail_spare = binval(8)
        self.composite_temp = binval(16)
        self.critical_warning = binval(8)

class identify_namespace(bitfield):
    def __init__(self):
        self.vendorspecific = binval(3712*8)
        self.rsvd3 = binval(192*8)
        self.lbaf15 = binval(4*8)
        self.lbaf14 = binval(4*8)
        self.lbaf13 = binval(4*8)
        self.lbaf12 = binval(4*8)
        self.lbaf11 = binval(4*8)
        self.lbaf10 = binval(4*8)
        self.lbaf9 = binval(4*8)
        self.lbaf8 = binval(4*8)
        self.lbaf7 = binval(4*8)
        self.lbaf6 = binval(4*8)
        self.lbaf5 = binval(4*8)
        self.lbaf4 = binval(4*8)
        self.lbaf3 = binval(4*8)
        self.lbaf2 = binval(4*8)
        self.lbaf1 = binval(4*8)
        self.lbaf0 = binval(4*8)
        self.eui64 = binval(8*8)
        self.nguid = binval(16*8)
        self.endgid = binval(16)
        self.nvmsetid = binval(16)
        self.nsattr = binval(8)
        self.rsvd2 = binval(3*8)
        self.anagrpid = binval(4*8)
        self.rsvd1 = binval(18*8)
        self.nows = binval(16)
        self.npda = binval(16)
        self.npdg = binval(16)
        self.npwa = binval(16)
        self.npwg = binval(16)
        self.nvmcap = binval(16*8)
        self.noiob = binval(16)
        self.nabspf = binval(16)
        self.nabo = binval(16)
        self.nabsn = binval(16)
        self.nacwu = binval(16)
        self.nawupf = binval(16)
        self.nawun = binval(16)
        self.dlfeat = binval(8)
        self.fpi = binval(8)
        self.rescap = binval(8)
        self.nmic = binval(8)
        self.dps = binval(8)
        self.dpc = binval(8)
        self.mc = binval(8)
        self.flbas = binval(8)
        self.nlbaf = binval(8)
        self.nsfeat = binval(8)
        self.nuse = binval(64)
        self.ncap = binval(64)
        self.nsze = binval(64)

class identify_ctrlr(bitfield):
    def __init__(self):
        self.vendorspecific = binval(1024*8)
        self.power_state_descriptor = binval(32*32*8)
        self.rsvd_nvme_over_fabrics = binval(256*8)
        self.rsvd_1024_1791 = binval(768*8)
        self.subnqn = binval(256*8)
        self.rsvd_540_767 = binval(228*8)
        self.sgls = binval(32)
        self.rsvd_534_535 = binval(16)
        self.acwu = binval(16)
        self.rsvd_531 = binval(8)
        self.nvscc = binval(8)
        self.awupf = binval(16)
        self.awun = binval(16)
        self.vwc = binval(8)
        self.fna = binval(8)
        self.fuses = binval(16)
        self.oncs = binval(16)
        self.nn = binval(32)
        self.maxcmd = binval(16)
        self.cqes = binval(8)
        self.sqes = binval(8)
        self.rsvd_332_511 = binval(180*8)
        self.sanicap = binval(32)
        self.mxtmt = binval(16)
        self.mntmt = binval(16)
        self.hctma = binval(16)
        self.kas = binval(16)
        self.fwug = binval(8)
        self.dsto = binval(8)
        self.edstt = binval(16)
        self.rpmbs = binval(32)
        self.unvmcap1 = binval(64)
        self.unvmcap0 = binval(64)
        self.tnvmcap1 = binval(64)
        self.tnvmcap0 = binval(64)
        self.hmmin = binval(32)
        self.hmpre = binval(32)
        self.mtfa = binval(16)
        self.cctemp = binval(16)
        self.wctemp = binval(16)
        self.apsta = binval(8)
        self.avscc = binval(8)
        self.npss = binval(8)
        self.elpe = binval(8)
        self.lpa = binval(8)
        self.frmw = binval(8)
        self.aerl = binval(8)
        self.acl = binval(8)
        self.oacs = binval(16)
        self.rsvd_240_255_mi = binval(16*8)
        self.rsvd_128_239 = binval(112*8)
        self.fguid = binval(16*8)
        self.rsvd_100_111 = binval(12*8)
        self.ctratt = binval(32)
        self.oaes = binval(32)
        self.rtd3e = binval(32)
        self.rtd3r = binval(32)
        self.ver = binval(32)
        self.cntlid = binval(16)
        self.mdts = binval(8)
        self.cmic = binval(8)
        self.ieee = binval(24)
        self.rab = binval(8)
        self.fr = binval(8*8)
        self.mn = binval(40*8)
        self.sn = binval(20*8)
        self.ssid = binval(16)
        self.vid = binval(16)

