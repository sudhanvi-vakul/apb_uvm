interface apb_if(input logic pclk);

  logic prst;
  logic psel;
  logic penable;
  logic pwrite;
  logic [31:0]pwdata;
  logic [31:0]prdata;
  logic [7:0]paddr;
  logic pready;
  logic pslverr;
  
  clocking cb @(posedge pclk);
    default input #1ns output #0ns;
    output psel,penable,pwrite,pwdata,paddr;
    input prst, prdata, pready, pslverr;
  endclocking
  
    // Modports
  modport drv (clocking cb, input prst,input pclk);
    modport mon (input pclk,prst, psel, penable, paddr, pwrite, pwdata, prdata, pready, pslverr);
    
  //Assertions
    
    //setup to access phase
   setup_to_access: assert property (@(posedge pclk)
    	disable iff (!prst)
    	(psel && !penable) |=> penable
  );
      
    //when psel and penable is high, the remaining signals should be stable
   all_sig_stable_accessphase: assert property (@(posedge pclk)
      	disable iff (!prst)
      	(psel && penable) |-> $stable(paddr) && $stable(pwrite) && $stable(pwdata)
  );
   //psel to be stable during access phase
    psel_stable: assert property (@(posedge pclk)
    	disable iff (!prst)
    	psel && penable |-> $stable(psel)
        ) else $error("APB ERROR: psel changed during access phase!");
  
endinterface