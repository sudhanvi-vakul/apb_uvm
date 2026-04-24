`include "apb_agent.sv"
`include "apb_scb.sv"
`include "apb_cov.sv"
class apb_env extends uvm_env;
  `uvm_component_utils(apb_env)
  apb_agent agt;
  apb_scoreboard scb;
  apb_coverage cvg;
  
  function new(string name,uvm_component parent);
    super.new(name,parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    agt = apb_agent::type_id::create("agt",this);
    scb = apb_scoreboard::type_id::create("scb",this);
    cvg = apb_coverage::type_id::create("cvg",this);
  endfunction
  
  function void connect_phase(uvm_phase phase);
    super.connect_phase(phase);
    agt.mon.ap_wr.connect(scb.ap_imp_wr);
    agt.mon.ap_rd.connect(scb.ap_imp_rd);
  endfunction
endclass