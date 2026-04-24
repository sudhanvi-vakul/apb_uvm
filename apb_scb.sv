`uvm_analysis_imp_decl(_wr)
`uvm_analysis_imp_decl(_rd)

class apb_scoreboard extends uvm_scoreboard;
  `uvm_component_utils(apb_scoreboard)
  bit [31:0]regfile[0:15];
  function new(string name,uvm_component parent);
    super.new(name,parent);
  endfunction
  
  uvm_analysis_imp_wr #(apb_write_struct, apb_scoreboard) ap_imp_wr;
  uvm_analysis_imp_rd #(apb_read_struct, apb_scoreboard) ap_imp_rd;
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);   
    ap_imp_wr = new("ap_imp_wr",this);
    ap_imp_rd = new("ap_imp_rd",this);
    
    foreach(regfile[i])
    	regfile[i] = '0;
  endfunction
  
  function void write_wr(apb_write_struct imp_wr);
    int index = imp_wr.addr[5:2];
    regfile[index] = imp_wr.data;
    `uvm_info("SCORE",$sformatf("WRITE regfile[0x%0h] = 0x%0h", imp_wr.addr, imp_wr.data), UVM_MEDIUM)
  endfunction
  
  function void write_rd(apb_read_struct imp_rd);
    int index = imp_rd.addr[5:2];
    if(regfile[index] == imp_rd.data)
      `uvm_info("SCORE",$sformatf("READ MATCHED addr=0x%0h exp=0x%0h act=0x%0h",
  imp_rd.addr, regfile[index], imp_rd.data), UVM_LOW)
     else
       `uvm_error("SCORE", $sformatf("READ MISMATCH addr=0x%0h exp=0x%0h act=0x%0h",
  imp_rd.addr, regfile[index], imp_rd.data))
       
  endfunction
  
endclass