{
   "_id": "_design/day_schema",
   "_rev": "13-5b5af63ba2b96a9cabe6444623ae4c41",
   "language": "javascript",
   "views": {
       "day_schema": {
           "map": "function(doc) { if(doc.type=='day_schema') {\n  emit(doc._id, doc)};\n}"
       },
       "slot_map": {
           "map": "function(doc) { \n  if(doc.type=='day_schema') {\n       for ( activity_row in doc.schema) {\n           var slot_row = doc.schema[activity_row];\n           var len = slot_row.length;\n           for(var i=1; i<len; i++) {\n               slot=slot_row[i];\n               emit([slot.slot_id, doc._id], [activity_row, slot])  } } } }"
       }
   }
}