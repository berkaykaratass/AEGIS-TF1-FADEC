pragma SPARK_Mode (On);

package AI_Decision_Engine is

   subtype RPM_Type is Float range 0.0 .. 120_000.0;
   subtype Fuel_Flow_Type is Float range 0.0 .. 5.0;
   subtype Temperature_Type is Float range 200.0 .. 2000.0;
   subtype Surge_Margin_Type is Float range -50.0 .. 100.0;
   subtype Thrust_Type is Float range 0.0 .. 200_000.0;
   subtype Probability_Type is Float range 0.0 .. 1.0;

   procedure Compute_Fuel_Command
     (Current_RPM     : in  RPM_Type;
      Target_RPM      : in  RPM_Type;
      EGT             : in  Temperature_Type;
      Surge_Margin    : in  Surge_Margin_Type;
      Fuel_Out        : out Fuel_Flow_Type)
   with
     Pre => (Current_RPM >= 0.0 and Target_RPM >= 0.0 and EGT >= 200.0),
     Post => (if EGT > 1050.0 or Surge_Margin < 0.0 then Fuel_Out = 0.0
              else Fuel_Out >= 0.0);

   function Evaluate_Surge_Risk
     (Flow_Op   : in Float;
      PR_Op     : in Float;
      Flow_Stall: in Float;
      PR_Stall  : in Float) return Probability_Type
   with
     Pre => (Flow_Op > 0.0 and PR_Op > 0.0 and Flow_Stall > 0.0 and PR_Stall > 0.0);

   procedure Emergency_Shutdown
     (Fuel_Out : out Fuel_Flow_Type)
   with
     Post => Fuel_Out = 0.0;

end AI_Decision_Engine;
