from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ValidationError
from starlette.requests import Request
import stripe
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = 'sk_test_51Mwu8xAfGedthlqWO2XlDLRMdyYtBKFLL1BO8FmUkoVwRZbAQe7YWnutEoRqqY7HMCmhSTk6x0ys4oVtBVXguu1w00hHTNwBlX'



class Item(BaseModel):
    id: int
    name: str
    picture_url: Optional[str] = None
    description: Optional[str] = None
    product_id: Optional[str] = None
    price: float
    quantity: int

class Cart(BaseModel):
    cart: List[Item]
@app.post("/create-checkout-session/{user_id}")
async def create_checkout_session(cart: Cart, user_id: int):
    customer = stripe.Customer.create()
    line_items = []

    for item in cart.cart:
        line_item = {
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": item.name,
                    "images": [item.picture_url] if item.picture_url else None,
                    "description": item.description,
                    "metadata": {
                        "id": item.product_id,
                    },
                },
                "unit_amount": int(item.price * 100),
            },
            "quantity": item.quantity,
        }
        line_items.append(line_item)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        shipping_address_collection={"allowed_countries": ["US", "CA"]},
        shipping_options=[
            {
                "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 0, "currency": "usd"},
                    "display_name": "Free shipping",
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 5},
                        "maximum": {"unit": "business_day", "value": 7},
                    },
                },
            },
            {
                "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 1500, "currency": "usd"},
                    "display_name": "Next day air",
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 1},
                        "maximum": {"unit": "business_day", "value": 1},
                    },
                },
            },
        ],
        customer=customer.id,
        metadata={"customer_id": user_id, "cart": json.dumps(cart.dict())},
        line_items=line_items,
        mode="payment",
        success_url="http://unn-w20015975.newnumyspace.co.uk/python/checkout-success",
        cancel_url="http://unn-w20015975.newnumyspace.co.uk/python/Cart",
    )

    return {"url": session.url}



endpoint_secret = 'whsec_773a59d6db6270ee4fb7100999b70dff5ae22df8532a4c7640756d0b74af9bba'
# Connect to the database

from datetime import datetime
# Establish a database connection
conn = sqlite3.connect("orders.db")
cur = conn.cursor()



@app.post('/webhook')
async def webhook(request: Request):
    event = None
    payload = await request.body()
    sig_header = request.headers['stripe-signature']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        print("Webhook verified")
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail='Invalid signature')

    # Check if the event type is checkout.session.completed
    if event['type'] == 'checkout.session.completed':
        data = event['data']['object']

        # Retrieve the customer details
        customer = stripe.Customer.retrieve(data['customer'])
       
        metadata = data['metadata']
        cart = json.loads(metadata['cart'])

        # Extract the required fields from the data dictionary
        customer_id = data['metadata']['customer_id']
        payment_status = data['payment_status']
        delivery_status = 'pending'

        for item in cart['cart']:
            picture_url = item['picture_url']
            name = item['name']
            quantity = item['quantity']
            product_price = data['amount_total'] / 100
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute("INSERT INTO orders (customer_id, picture_url, name, product_price, payment_status, delivery_status, date,quantity) VALUES (?, ?, ?, ?, ?, ?, ?,?)",
                        (customer_id, picture_url, name, product_price, payment_status, delivery_status, date,quantity))
            
        # Commit the transaction
        conn.commit()
        # Insert the order into the database

    return JSONResponse(content={'success': True})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=4242)

    # Close the database connection
    conn.close()
@app.get("/orders/{user_id}")
def get_cart(user_id: int):
    # create a new database connection
    conn = sqlite3.connect("orders.db")
    with conn:
        cur = conn.cursor()
        # get all rows from the cart table for the specified user
        cur.execute("SELECT * FROM orders WHERE  customer_id=?", (user_id,))
        rows = cur.fetchall()
        if not rows:
            return {"message": "User not found"}
        products = []
        for row in rows:
            products.append({"id": row[0], "user_id": row[1], "picture_url": row[2], "name": row[3],"total":row[4],"pay_status":row[5],"ship":row[6],"date":row[7],"quantity":row[8]})
        return products
