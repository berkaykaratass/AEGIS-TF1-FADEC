pragma SPARK_Mode (On);

package body Contract_Validator is

   function Is_Status_Valid (Status : Engine_Status_t) return Boolean is
   begin
      return (Status.Speed >= 0.0 and Status.Speed <= 120_000.0) and
             (Status.Temp >= 0.0 and Status.Temp <= 2500.0) and
             (Status.Pressure >= 0.0 and Status.Pressure <= 30.0) and
             (Status.Vib >= 0.0 and Status.Vib <= 20.0);
   end Is_Status_Valid;

   function Is_Envelope_Safe (Status : Engine_Status_t) return Boolean is
      Safe : Boolean := True;
   begin
      if Status.Speed > 105_000.0 then
         Safe := False;
      elsif Status.Temp > 1050.0 then
         Safe := False;
      elsif Status.Pressure > 15.0 then
         Safe := False;
      elsif Status.Vib > 5.0 then
         Safe := False;
      end if;

      return Safe;
   end Is_Envelope_Safe;

end Contract_Validator;
