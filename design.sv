// Code your design here
module apb_slave(pclk,prst,psel,penable,pwrite,pwdata,prdata,paddr,pready,pslverr);
  input pclk,prst,psel,penable,pwrite;
  input [31:0]pwdata;
  input [7:0]paddr;
  output logic pready,pslverr;
  output logic [31:0]prdata;
  //4 byte alignment 
  logic [31:0]regfile[0:15];
  logic [3:0] index;
  
  assign index = paddr[5:2];
  
  //make pready as 1 by default and pslverr as error free
  assign pready = 1'b1;
  assign pslverr = 1'b0;
  
  //read
  always_comb begin
    if(psel && penable && !pwrite && (index < 16))
      prdata = regfile[index];
    else
      prdata = 32'h0;
  end
  
  //write
  always_ff@(posedge pclk or negedge prst)begin
    if(!prst)begin
      for(int i=0;i<=15;i++)begin
        regfile[i] <= 32'h0;
      end
    end
      
    else
      if(psel && penable && pwrite && (index < 16))
        regfile[index] <= pwdata;
  end
endmodule