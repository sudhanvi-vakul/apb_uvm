typedef struct packed{bit [7:0]addr; bit [31:0]data;} apb_write_struct;
typedef struct packed{bit [7:0]addr; bit [31:0]data;} apb_read_struct;

class apb_mon extends uvm_monitor;
  `uvm_component_utils(apb_mon)
  virtual apb_if.mon vif;
  uvm_analysis_port#(apb_write_struct) ap_wr;
  uvm_analysis_port#(apb_read_struct) ap_rd;
  
  function new(string name, uvm_component parent);
    super.new(name,parent);
  endfunction
  
  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    ap_wr = new("ap_wr",this);
    ap_rd = new("ap_rd",this);
    if (! uvm_config_db #(virtual apb_if.mon) :: get (this, "", "vif", vif)) 		begin
      `uvm_fatal("NoVIF","DUT interface not found");
    end
  endfunction
  
  task run_phase(uvm_phase phase);
    apb_write_struct wr_s;
    apb_read_struct rd_s;
    
    forever begin
      @(posedge vif.pclk);
      if(vif.psel && vif.penable)begin
        if(vif.pwrite && vif.pready)begin
          wr_s.addr = vif.paddr;
          wr_s.data = vif.pwdata;
          ap_wr.write(wr_s);
        end
       if(!vif.pwrite && vif.pready)begin
          rd_s.addr = vif.paddr;
          rd_s.data = vif.prdata;
          ap_rd.write(rd_s);
        end
      end
    end
  endtask
  
  
endclass