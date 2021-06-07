import requests
from twilio.rest import Client
from bs4 import BeautifulSoup
from selenium import webdriver
from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, ValidationError
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_APP_KEY')
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///products.db"
db = SQLAlchemy(app)

# twilio account
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_ID")
AUTH_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

# Configure database where user's and product's info is stored
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=False, nullable=False)
    phone_number = db.Column(db.Integer, unique=False, nullable=False)
    product_name = db.Column(db.String(250), unique=False, nullable=False)
    product_price = db.Column(db.Integer, unique=False, nullable=False)
    product_url = db.Column(db.String(250), unique=False, nullable=False)
    target_price = db.Column(db.Integer, unique=False, nullable=False)
    any_sale = db.Column(db.String(250), unique=False, nullable=False)

    def __repr__(self):
        return '<Product %r>' % self.title

db.create_all()

# Class to identify error when user inputs a desired price that's greater than the current price of the item
class PriceError(object):
    def __init__(self, model):
        self.model = model
        self.message = "The current price of the item is less than this amount!"

    def __call__(self, form, target_price):
        user = self.model.query.filter_by(id=self.model.query.count()).first()
        check = self.model.query.filter(int(target_price.data) > user.product_price).first()
        if check:
            raise ValidationError(self.message)

# Configure forms for user to enter name, phone number, amazon url, target price/sale
class ItemForm(FlaskForm):
    name = StringField('Your name', validators=[DataRequired()])
    phone = IntegerField('Your phone number', validators=[DataRequired()])
    amazon_url = StringField('Product URL', validators=[DataRequired()])
    submit = SubmitField('Submit')

class CriteriaForm(FlaskForm):
    target_price = StringField("What is the most you're willing to pay?",
                               validators=[DataRequired(),
                                           PriceError(
                                               Product,
                                           )])
    any_sale = SelectField('Would you like to be notified when the item goes on sale for any amount?',
                           choices=['Yes', 'No'])
    submit = SubmitField('Submit')

# Function to scrape amazon link for product name and price using beautifulsoup (only intermittently works)
def scrape_site(product_url):
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0"
    accept_language = "en-US,en;q=0.5"
    headers = {
        "accept-language": accept_language,
        "user-agent": user_agent
    }

    response = requests.get(url=product_url, headers=headers)
    response.raise_for_status()
    amazon_html = response.text

    soup = BeautifulSoup(amazon_html, "lxml")

    find_price = soup.find("span", id="priceblock_ourprice").text()
    find_price = find_price.replace(u"\xa0", u" ")
    find_price = find_price.replace("$", "")
    product_price = float(find_price.split(" ")[0])

    product_name = soup.find(id="productTitle").getText().strip()
    product_name = product_name.encode("ascii", errors="ignore").decode()

    product_details = {"price": product_price,
                       "name": product_name}

    return product_details

# Function to scrape amazon using selenium
def scrape_site_selenium(product_url):
    chrome_driver_path = "C:\Development\chromedriver.exe"
    opt = webdriver.ChromeOptions()
    opt.add_argument('headless')
    driver = webdriver.Chrome(executable_path=chrome_driver_path, options=opt)

    driver.get(
        f"{product_url}")

    find_price = driver.find_element_by_xpath("//span[@id='priceblock_ourprice']")
    find_price = find_price.text
    find_price = find_price.replace("$", "")
    product_price = float(find_price)

    product_name = driver.find_element_by_xpath("//span[@id='productTitle']")
    product_name = product_name.text

    product_details = {"price": product_price,
                       "name": product_name}

    return product_details

# Function to send initial confirmation text
def send_first_text(current):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    current_user = Product.query.filter_by(id=current).first()
    message = client.messages \
        .create(
        body=f"Hey {current_user.username}! We'll make sure to text you when {current_user.product_name} is "
             f"below your desired price of {current_user.target_price}. Stay tuned!",
        from_=TWILIO_PHONE,
        to=f"+1{current_user.phone_number}"
    )

# Function to send text once desired price is achieved
def send_sale_text():
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    for row in Product.query.filter(Product.product_price < Product.target_price).all():
        message = client.messages \
            .create(
            body=f"Hi {row.username}! {row.product_name} is now below your desired price of ${row.target_price}!"
              f"Check it out here: {row.product_url}",
            from_=TWILIO_PHONE,
            to=f"+1{row.phone_number}"
        )

        # Delete row from database
        db.session.delete(row)

# Website

@app.route("/", methods=['GET', 'POST'])
def home():
    item_form = ItemForm()
    if item_form.validate_on_submit():
        user_name = request.form['name']
        user_phone = request.form['phone']
        user_amazon_url = request.form['amazon_url']
        user_product_details = scrape_site_selenium(user_amazon_url)
        new_entry = Product(
            username=user_name,
            phone_number=user_phone,
            product_name=user_product_details['name'],
            product_price=user_product_details['price'],
            product_url=user_amazon_url,
            any_sale="",
            target_price=0,
        )
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for("details", product_id=new_entry.id))
    return render_template("index.html", item_form=item_form)

@app.route("/details/<product_id>", methods=['GET', 'POST'])
def details(product_id):
    current_user = Product.query.filter_by(id=product_id).first()
    detail_form = CriteriaForm()
    product_name = current_user.product_name
    product_price = current_user.product_price
    if detail_form.validate_on_submit():
        current_user.target_price = request.form["target_price"]
        current_user.any_sale = request.form["any_sale"]
        db.session.commit()
        # send_first_text(product_id)
        return redirect(url_for("confirmation"))
    return render_template("details.html", detail_form=detail_form, p_name=product_name, p_price=product_price)

@app.route("/confirmation")
def confirmation():
    return render_template("confirmation.html")



if __name__ == '__main__':
    app.run(debug=True)

send_sale_text()