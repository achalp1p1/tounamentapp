from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime
import json
import configparser
from database.database_init import get_db_connection, init_database

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Initialize database on startup
init_database()

if __name__ == '__main__':
    app.run(debug=True) 