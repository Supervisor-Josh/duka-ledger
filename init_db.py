from database import engine
import models

print("Creating database tables...")
models.Base.metadata.create_all(bind=engine)
print("Tables created successfully! Look out for 'duka.db' in your project folder.")
