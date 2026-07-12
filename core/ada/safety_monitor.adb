pragma SPARK_Mode (On);

package body Safety_Monitor is

   procedure Process_Safety
     (State        : in out Safety_State;
      Raw_Egt      : in     EGT_Type;
      Raw_N1       : in     N1_RPM_Type;
      Raw_P3       : in     P3_Type;
      Raw_Vib      : in     Vibration_Type;
      Requested_Wf : in     Fuel_Flow_Type;
      Safe_Wf      : out    Fuel_Flow_Type;
      Verdict      : out    Safety_Verdict;
      DT           : in     Float)
   is
      Absolute_Max_Egt : constant Float := 1050.0;
      Absolute_Max_N1  : constant Float := 105000.0;
      Absolute_Max_P3  : constant Float := 15.0;
      Absolute_Max_Vib : constant Float := 5.0;
      
      Veto_Active : Boolean := False;
   begin
      -- 1. Immediate structural checks
      if Raw_N1 > Absolute_Max_N1 or Raw_P3 > Absolute_Max_P3 then
         Veto_Active := True;
      end if;

      -- 2. Debounced EGT check (20 ms debounce)
      if Raw_Egt > Absolute_Max_Egt then
         State.Egt_Overshoot_Timer := State.Egt_Overshoot_Timer + DT;
         if State.Egt_Overshoot_Timer >= 0.020 then
            Veto_Active := True;
         end if;
      else
         State.Egt_Overshoot_Timer := 0.0;
      end if;

      -- 3. Debounced Vibration check (20 ms debounce)
      if Raw_Vib > Absolute_Max_Vib then
         State.Vibration_Overshoot_Timer := State.Vibration_Overshoot_Timer + DT;
         if State.Vibration_Overshoot_Timer >= 0.020 then
            Veto_Active := True;
         end if;
      else
         State.Vibration_Overshoot_Timer := 0.0;
      end if;

      -- 4. Apply verdict and outputs
      if Veto_Active or State.Trip_Active then
         State.Trip_Active := True;
         Verdict := Emergency_Shutdown;
         Safe_Wf := 0.0;
      else
         Verdict := Pass;
         Safe_Wf := Requested_Wf;
      end if;
   end Process_Safety;

end Safety_Monitor;
