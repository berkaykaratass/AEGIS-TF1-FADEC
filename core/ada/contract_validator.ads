pragma SPARK_Mode (On);

package Contract_Validator is

   type Engine_Status_t is record
      Speed    : Float;
      Temp     : Float;
      Pressure : Float;
      Vib      : Float;
   end record;

   function Is_Status_Valid (Status : Engine_Status_t) return Boolean;

   function Is_Envelope_Safe (Status : Engine_Status_t) return Boolean
   with
     Pre => Is_Status_Valid (Status);

end Contract_Validator;
