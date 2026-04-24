class apb_base_seq extends uvm_sequence#(apb_txn);
  `uvm_object_utils(apb_base_seq)
  
  function new(string name="apb_base_seq");
    super.new(name);
  endfunction

endclass

class apb_smoke_seq extends apb_base_seq;
  `uvm_object_utils(apb_smoke_seq)
  
  function new(string name="apb_smoke_seq");
    super.new(name);
  endfunction
  
  task body();
    apb_txn t;
    //write
    for(int i=0;i<4;i++)begin
      t = apb_txn::type_id::create($sformatf("write_%0d",i));
      start_item(t);
      assert(t.randomize() with {
        write == 1;
        addr == (8'h00 + i*4);
        data == (32'hA5A5_0000 + i);
        idle_cycles == 1;});
      finish_item(t);
    end
    
    //read
    for(int i=0;i<4;i++)begin
      t = apb_txn::type_id::create($sformatf("write_%0d",i));
      start_item(t);
      assert(t.randomize() with {
        write == 0;
        addr == (8'h00 + i*4);
        idle_cycles == 1;});
      finish_item(t);
    end
  endtask
endclass

class apb_write_read_seq extends apb_base_seq;
  `uvm_object_utils(apb_write_read_seq)
  
  function new(string name="apb_write_read_seq");
    super.new(name);
  endfunction
  
  task body();
    apb_txn t;
    //write
    for(int i=0;i<8;i++)begin
      t = apb_txn::type_id::create($sformatf("write_%0d",i));
      start_item(t);
      assert(t.randomize() with {
        write == 1;
        addr == (8'h00 + i*4);
        idle_cycles == 1;});
      finish_item(t);
    end
    
    //read
    for(int i=0;i<8;i++)begin
      t = apb_txn::type_id::create($sformatf("write_%0d",i));
      start_item(t);
      assert(t.randomize() with {
        write == 0;
        addr == (8'h00 + i*4);
        idle_cycles == 1;});
      finish_item(t);
    end
  endtask
endclass

class apb_back2back_seq extends apb_base_seq;
  `uvm_object_utils(apb_back2back_seq)
  
  function new(string name="apb_back2back_seq");
    super.new(name);
  endfunction
  
  task body();
    apb_txn t;
    //write
    for(int i=0;i<4;i++)begin
      t = apb_txn::type_id::create($sformatf("write_%0d",i));
      start_item(t);
      assert(t.randomize() with {
        write == 1;
        addr == (8'h00 + i*4);
        data == (32'hA5A5_0000 + i);
        idle_cycles == 0;});
      finish_item(t);
    end
    
    //read
    for(int i=0;i<4;i++)begin
      t = apb_txn::type_id::create("b2b");
      start_item(t);
      assert(t.randomize() with {
        write == 0;
        addr == (8'h00 + i*4);
        idle_cycles == 0;});
      finish_item(t);
    end
  endtask
endclass

class apb_random_seq extends apb_base_seq;
  `uvm_object_utils(apb_random_seq)
  
  function new(string name="apb_random_seq");
    super.new(name);
  endfunction
  
  task body();
    apb_txn t;

    for(int i=0;i<1000;i++)begin
      t = apb_txn::type_id::create("random");
      start_item(t);
      assert(t.randomize());
      finish_item(t);
    end

  endtask
endclass

