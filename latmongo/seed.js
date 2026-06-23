db = db.getSiblingDB('latihan');

db.todo.drop();

var uuid = UUID();
var uuidStr = uuid.toString();
// extract just the UUID value: UUID("xxx") -> xxx
uuidStr = uuidStr.substring(6, uuidStr.length - 2);

db.todo.insert({
  user_id: uuidStr,
  title: "Coba Todo List",
  description: "Coba saja",
  created_at: new Date(),
  updated_at: new Date()
});

print("=== USERS ===");
db.users.find().forEach(printjson);
print("=== TODO ===");
db.todo.find().forEach(printjson);
