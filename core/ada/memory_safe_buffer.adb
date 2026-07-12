pragma SPARK_Mode (On);

package body Memory_Safe_Buffer is

   function Is_Full (Buffer : Buffer_Type) return Boolean is
   begin
      return Buffer.Count = Size;
   end Is_Full;

   function Is_Empty (Buffer : Buffer_Type) return Boolean is
   begin
      return Buffer.Count = 0;
   end Is_Empty;

   function Length (Buffer : Buffer_Type) return Natural is
   begin
      return Buffer.Count;
   end Length;

   procedure Push (Buffer : in out Buffer_Type; Element : in Element_Type) is
   begin
      Buffer.Elements (Buffer.Head) := Element;
      
      if Buffer.Head = Index_Type'Last then
         Buffer.Head := Index_Type'First;
      else
         Buffer.Head := Buffer.Head + 1;
      end if;
      
      Buffer.Count := Buffer.Count + 1;
   end Push;

   procedure Pop (Buffer : in out Buffer_Type; Element : out Element_Type) is
   begin
      Element := Buffer.Elements (Buffer.Tail);
      
      if Buffer.Tail = Index_Type'Last then
         Buffer.Tail := Index_Type'First;
      else
         Buffer.Tail := Buffer.Tail + 1;
      end if;
      
      Buffer.Count := Buffer.Count - 1;
   end Pop;

end Memory_Safe_Buffer;
