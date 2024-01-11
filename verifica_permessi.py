from database import Database
import datetime

# Crea un'istanza della classe Database
database_instance = Database()
db = database_instance.get_db()

def estrai_permessi(user_id):
    user_document = db.Users.find_one({"user_id": user_id})
                    
    if user_document:
        return user_document.get('permessi', None)
    else:
        return None

def controllo_permessi(permesso):
    if permesso is None:
        print("Guest")
    elif permesso == 0:
        print("Visitatore")
    elif permesso == 1:
        print("Utente")
    elif permesso == 2:
        print("Utente Premium")
    elif permesso == 3:
        print("Admin")
    elif permesso == 4:
        print("Gestore")

# Esempio di utilizzo
if __name__ == '__main__':
    #user_id = "123456"  # Sostituisci con un vero user_id
    permesso = estrai_permessi(user_id)
    controllo_permessi(permesso)
