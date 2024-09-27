from django.conf import settings

import stripe

class ShStripe:
    def __init__(self, api_key=""):
        self.api_key = api_key
        try:
            self.return_url = settings.STRIPE_RETURN_URL
            self.success_url = settings.STRIPE_SUCCESS_URL
            self.cancel_url = settings.STRIPE_CANCEL_URL
            self.return_pay_url = settings.STRIPE_RETURN_PAY_URL
        except:
            self.return_url = ""
            self.success_url = ""
            self.cancel_url = ""
            self.return_pay_url = ""


    def create_stripe_payment_intent(self, customer_id, payment_method_id, amount, currency="eur"):
        stripe.api_key = self.api_key

        try:
            next_action = ""
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                payment_method=payment_method_id,
                automatic_payment_methods={ 'enabled': True, },
                setup_future_usage='on_session',
                return_url=self.return_pay_url,
                confirm=True
            )
            if payment_intent.next_action != None:
                if payment_intent.next_action.redirect_to_url != None:
                    next_action = payment_intent.next_action.redirect_to_url.url

            return payment_intent.id, next_action
        except stripe.error.StripeError as e:
            print(f"Error creating Stripe payment intent: {e}")
            return None

    def get_session (self, session_id):
        stripe.api_key = self.api_key
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session
        except stripe.error.StripeError as e:
            print(f"Error getting Stripe session: {e}")
            return None

    def verify_payment_intent(self, payment_intent_id):
        stripe.api_key = self.api_key
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return payment_intent
        except stripe.error.StripeError as e:
            print(f"Error verifying Stripe payment intent: {e}")
            return None


