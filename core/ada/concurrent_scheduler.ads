pragma SPARK_Mode (On);

package Concurrent_Scheduler is

   protected type Safety_Monitor is
      procedure Trip_Emergency_Shutdown;
      procedure Clear_Faults;
      function Is_Emergency_Active return Boolean;
   private
      Emergency_Active : Boolean := False;
   end Safety_Monitor;

   protected type Telemetry_Buffer is
      procedure Write_Value (Val : in Float);
      procedure Read_Value (Val : out Float);
   private
      Latest_Value   : Float := 0.0;
      Has_New_Value  : Boolean := False;
   end Telemetry_Buffer;

end Concurrent_Scheduler;
