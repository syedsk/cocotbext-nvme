
`resetall
`timescale 1 ns / 1 ps
`default_nettype none

module test_cosim_nvme;
    reg         clk = 0;
    reg         rstn = 0;

    // input AXI-stream (1 byte)
    wire        i_tready;
    reg         i_tvalid = 0;
    reg  [7:0]  i_tdata  = 0;
    reg         i_tlast  = 0;

    // output AXI-stream (4 byte)
    reg         o_tready = 0;
    wire        o_tvalid;
    wire [31:0] o_tdata;
    wire        o_tlast;
    wire [3:0]  o_tkeep;

    // always #5 clk = ~clk;   // 100 MHz

    gzip_compressor_top #(
        .SIMULATION(1)
    ) u_gzip (
        .rstn     (rstn),
        .clk      (clk),
        .i_tready (i_tready),
        .i_tvalid (i_tvalid),
        .i_tdata  (i_tdata),
        .i_tlast  (i_tlast),
        .o_tready (o_tready),
        .o_tvalid (o_tvalid),
        .o_tdata  (o_tdata),
        .o_tlast  (o_tlast),
        .o_tkeep  (o_tkeep)
    );
endmodule
