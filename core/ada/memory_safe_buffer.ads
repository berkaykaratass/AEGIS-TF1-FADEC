pragma SPARK_Mode (On);

generic
   Size : Positive;
   type Element_Type is private;
package Memory_Safe_Buffer is

   type Buffer_Type is private;

   function Is_Full (Buffer : Buffer_Type) return Boolean;
   function Is_Empty (Buffer : Buffer_Type) return Boolean;
   function Length (Buffer : Buffer_Type) return Natural;

   procedure Push (Buffer : in out Buffer_Type; Element : in Element_Type)
   with
     Pre  => not Is_Full (Buffer),
     Post => Length (Buffer) = Length (Buffer)'Old + 1;

   procedure Pop (Buffer : in out Buffer_Type; Element : out Element_Type)
   with
     Pre  => not Is_Empty (Buffer),
     Post => Length (Buffer) = Length (Buffer)'Old - 1;

private

   type Index_Type is range 0 .. Size - 1;
   type Element_Array is array (Index_Type) of Element_Type;

   type Buffer_Type is record
      Elements : Element_Array;
      Head     : Index_Type := 0;
      Tail     : Index_Type := 0;
      Count    : Natural := 0;
   end record;

end Memory_Safe_Buffer;
