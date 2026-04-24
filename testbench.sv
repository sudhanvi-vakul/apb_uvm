// Code your testbench here
// or browse Examples
`timescale 1ns/1ps
import uvm_pkg::*; 

`include "uvm_macros.svh"
`include "apb_if.sv"
`include "apb_test.sv"

module tb_top;
  logic pclk;
  always #5 pclk = ~pclk;
  apb_if vif(pclk);
  
  
  apb_slave dut(.pclk(vif.pclk),
                .prst(vif.prst),
                .psel(vif.psel),
                .penable(vif.penable),
                .pwrite(vif.pwrite),
                .pwdata(vif.pwdata),
                .prdata(vif.prdata),
                .paddr(vif.paddr),
                .pready(vif.pready),
                .pslverr(vif.pslverr));
  
  initial begin
    $dumpfile("dump.vcd"); // Specifies the output file name
    $dumpvars(0, tb_top);  // Record all signals in tb_top and below
  end
  
  initial begin
    vif.prst = 0;pclk = 0;
    repeat(1)@(posedge pclk);
      vif.prst = 1;
  end
  initial begin
    uvm_config_db#(virtual apb_if.drv)::set(null, "uvm_test_top", "vif_drv", vif);
    uvm_config_db#(virtual apb_if.mon)::set(null, "uvm_test_top", "vif_mon", vif);
  	run_test();
  end
  
                
endmodule