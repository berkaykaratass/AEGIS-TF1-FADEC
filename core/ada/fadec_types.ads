pragma SPARK_Mode (On);

package FADEC_Types is

   subtype N1_RPM_Type       is Float range 0.0 .. 115_000.0;
   subtype EGT_Type          is Float range 0.0 .. 2_000.0;
   subtype P3_Type           is Float range 0.0 .. 25.0;
   subtype Fuel_Flow_Type    is Float range 0.0 .. 100.0;
   subtype Vibration_Type    is Float range 0.0 .. 20.0;
   subtype Stator_Angle_Type is Float range -30.0 .. 60.0;
   subtype Voltage_Type      is Float range 0.0 .. 50.0;

   type Guard_Result is record
      Inhibit    : Boolean := False;
      Safe_Value : Fuel_Flow_Type := 0.0;
   end record;

   type Safety_Verdict is (Pass, Inhibit, Emergency_Shutdown);

end FADEC_Types;
