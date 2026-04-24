class apb_drv extends uvm_driver#(apb_txn);
  `uvm_component_utils(apb_drv)
  virtual apb_if.drv vif;
  
  function new(string name,uvm_component parent);
    super.new(name,parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    if (! uvm_config_db #(virtual apb_if.drv) :: get (this, "", "vif", vif)) 		begin
      `uvm_fatal("NoVIF","DUT interface not found")
    end
  endfunction
  
  task run_phase(uvm_phase phase);
    apb_txn t;
    //Initialize the values
      vif.cb.psel <= 1'b0;
      vif.cb.penable <= 1'b0;
      vif.cb.pwrite <= 1'b0;
      vif.cb.paddr <= 1'b0;
      vif.cb.pwdata <= 1'b0;
    	@(posedge vif.pclk);
    
    forever begin
      seq_item_port.get_next_item (t);
      repeat(t.idle_cycles)
        @(posedge vif.pclk);
      //SETUP Phase
      vif.cb.psel <= 1'b1;
      vif.cb.penable <= 1'b0;
      vif.cb.pwrite <= t.write;
      vif.cb.paddr <= t.addr;
      vif.cb.pwdata <= t.data;
      @(posedge vif.pclk);
      
      //ACCESS Phase
      vif.cb.penable <= 1'b1;
      @(posedge vif.pclk);
      while(vif.cb.pready == 0)
      	@(posedge vif.pclk);
      
      //Deassert phase
      
      vif.cb.psel <= 1'b0;
      vif.cb.penable <= 1'b0;
      
      seq_item_port.item_done ();
    end
    
  endtask
  
endclass