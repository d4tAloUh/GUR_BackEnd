# GUR (Glovo-Uber-Raketa sample) Backend
#### Built with Django DRF + pyJWT + Postgis

## Build Setup

### Pre-requirements
#### You have to install postgres 12.6 version
#### You have to install postgis 3.1 version [windows installation](https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/#windows)
#### Or you could use postgis docker image with command
```bash
docker run --name gur-postgis -e POSTGRES_PASSWORD=gur-postgis -d postgis/postgis -p 5432:5432
```

### Installation
```bash
# install dependencies
$ pip install -r requirements.txt

# migrate database
$ python manage.py makemigrations 
$ python manage.py migrate 
# if you want to populate database with existing data, use: 
$ python manage.py loaddata db.json

# start serving on 8000 port
$ python manage.py runserver 
```

```bash
# run tests
python manage.py test --pattern "test_*.py"
```

```bash
# test users:
# user:
test@gmail.com
qwe123

# admin:
admin@gmail.com
qwe123

# courier:
courier@gmail.com
qwe123
```

### Frequently asked questions

#### The sockets returns `rejected`
```bash
Probably the host does not match the allowed hosts in settings (check that front is running on localhost or 127.0.0.1)
```