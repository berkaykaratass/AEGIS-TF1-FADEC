pragma SPARK_Mode (On);

package body Concurrent_Scheduler is

   protected body Safety_Monitor is
      
      procedure Trip_Emergency_Shutdown is
      begin
         Emergency_Active := True;
      end Trip_Emergency_Shutdown;

      procedure Clear_Faults is
      begin
         Emergency_Active := False;
      end Clear_Faults;

      function Is_Emergency_Active return Boolean is
      begin
         return Emergency_Active;
      end Is_Emergency_Active;

   end Safety_Monitor;

   protected body Telemetry_Buffer is

      procedure Write_Value (Val : in Float) is
      begin
         Latest_Value := Val;
         Has_New_Value := True;
      end Write_Value;

      procedure Read_Value (Val : out Float) is
      begin
         Val := Latest_Value;
         Has_New_Value := False;
      end Read_Value;

   end Telemetry_Buffer;

end Concurrent_Scheduler;
