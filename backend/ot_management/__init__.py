import pymysql

# Instalar pymysql como driver de MySQL
pymysql.install_as_MySQLdb()

# Truco: Engañar a Django para que crea que tenemos una versión compatible
import MySQLdb
if not hasattr(MySQLdb, 'version_info'):
    MySQLdb.version_info = (2, 2, 1, 'final', 0)
    
# Por si acaso, forzamos la versión en string también
if not hasattr(MySQLdb, '__version__'):
    MySQLdb.__version__ = '2.2.1'
elif MySQLdb.__version__ < '2.2.1':
    MySQLdb.version_info = (2, 2, 1, 'final', 0)
    MySQLdb.__version__ = '2.2.1'