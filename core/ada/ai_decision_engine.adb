pragma SPARK_Mode (On);

package body AI_Decision_Engine is

   procedure Compute_Fuel_Command
     (Current_RPM     : in  RPM_Type;
      Target_RPM      : in  RPM_Type;
      EGT             : in  Temperature_Type;
      Surge_Margin    : in  Surge_Margin_Type;
      Fuel_Out        : out Fuel_Flow_Type)
   is
   begin
      if EGT > 1050.0 or Surge_Margin < 0.0 then
         Fuel_Out := 0.0;
      else
         declare
            Delta_RPM : Float := Target_RPM - Current_RPM;
            Base_Fuel : Float := 0.05 + (Current_RPM / 120_000.0) * 2.0;
         begin
            if Delta_RPM > 0.0 then
               Base_Fuel := Base_Fuel + (Delta_RPM * 0.0001);
            else
               Base_Fuel := Base_Fuel + (Delta_RPM * 0.00005);
            end if;

            /* Clamp to subtype range */
            if Base_Fuel < 0.05 then
               Fuel_Out := 0.05;
            elsif Base_Fuel > 4.5 then
               Fuel_Out := 4.5;
            else
               Fuel_Out := Base_Fuel;
            end if;
         end;
      end if;
   end Compute_Fuel_Command;

   function Evaluate_Surge_Risk
     (Flow_Op   : in Float;
      PR_Op     : in Float;
      Flow_Stall: in Float;
      PR_Stall  : in Float) return Probability_Type
   is
      Margin : Float;
      Risk   : Float;
   begin
      Margin := ((Flow_Op * PR_Stall) / (Flow_Stall * PR_Op)) - 1.0;
      if Margin < 0.0 then
         Risk := 1.0;
      elsif Margin > 0.5 then
         Risk := 0.0;
      else
         Risk := 1.0 - (Margin / 0.5);
      end if;

      /* Clamp to Probability_Type */
      if Risk < 0.0 then
         return 0.0;
      elsif Risk > 1.0 then
         return 1.0;
      else
         return Risk;
      end if;
   end Evaluate_Surge_Risk;

   procedure Emergency_Shutdown
     (Fuel_Out : out Fuel_Flow_Type)
   is
   begin
      Fuel_Out := 0.0;
   end Emergency_Shutdown;

end AI_Decision_Engine;
