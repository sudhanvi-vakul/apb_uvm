class apb_coverage extends uvm_component;
  `uvm_component_utils(apb_coverage)
  virtual apb_if.mon vif;
    
  
  covergroup cg;
    option.per_instance = 1;
    sel: coverpoint vif.psel;
    enable: coverpoint vif.penable;
    write: coverpoint vif.pwrite;

    addr: coverpoint vif.paddr iff (vif.psel && vif.penable && vif.pready) {
      bins regs_0_7  = {[8'h00:8'h1C]};
      bins regs_8_15 = {[8'h20:8'h3C]};
    }

    rdata : coverpoint vif.prdata iff (vif.psel && vif.penable && vif.pready && !vif.pwrite) {
      bins zero  = {32'h0000_0000};
      bins other = default;
    }

     addr_and_rw : cross vif.paddr, vif.pwrite iff (vif.psel && vif.penable && vif.pready);

  endgroup
  
  function new(string name, uvm_component parent);
    super.new(name,parent);
    cg = new();
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (! uvm_config_db #(virtual apb_if.mon) :: get (this, "", "vif", vif)) 		begin
      `uvm_fatal("NoVIF","DUT interface not found")
    end   
  endfunction
  
  task run_phase(uvm_phase phase);
      forever begin
        @(posedge vif.pclk);
        if (vif.psel && vif.penable && vif.pready)
          cg.sample();
      end
  endtask
  
  function void report_phase(uvm_phase phase);
  super.report_phase(phase);
  `uvm_info(get_type_name(), 
            $sformatf("Coverage = %.2f%%", cg.get_coverage()), 
            UVM_LOW)
endfunction

  
endclass