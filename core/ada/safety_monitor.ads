pragma SPARK_Mode (On);
with FADEC_Types; use FADEC_Types;

package Safety_Monitor is

   type Safety_State is record
      Egt_Overshoot_Timer       : Float := 0.0;
      Vibration_Overshoot_Timer : Float := 0.0;
      Trip_Active               : Boolean := False;
   end record;

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
   with
     Pre => DT > 0.0,
     Post => (if Verdict = Emergency_Shutdown then Safe_Wf = 0.0
              else Safe_Wf = Requested_Wf);

end Safety_Monitor;
