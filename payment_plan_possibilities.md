Adding a credit system with payments is actually quite straightforward with your existing authentication. Here's my assessment:

## Difficulty: **Moderate** (2-3 days of work)

### What You Need to Add

**1. Database Changes (Easy)**
```python
# In models.py, add to existing user or create:
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))
    credits = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CreditTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Integer)  # Positive for purchase, negative for usage
    type = db.Column(db.String(50))  # 'purchase', 'usage', 'admin_grant'
    stripe_payment_id = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

**2. Credit Check Wrapper (Easy)**
```python
def requires_credits(credits_needed=1):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if user.credits < credits_needed:
                return jsonify({'error': 'Insufficient credits'}), 402
            
            # Deduct credits
            user.credits -= credits_needed
            log_credit_usage(user.id, credits_needed)
            db.session.commit()
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# Apply to AI endpoint:
@app.route('/api/tasks/parse', methods=['POST'])
@login_required
@requires_credits(1)
def parse_task():
    # existing code...
```

**3. Payment Integration (Moderate)**

**Stripe is the easiest option**. Two approaches:

**Option A: Simple Checkout (Recommended for MVP)**
```python
import stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@app.route('/api/credits/purchase', methods=['POST'])
@login_required
def purchase_credits():
    data = request.json
    package = data.get('package')  # 'small', 'medium', 'large'
    
    packages = {
        'small': {'credits': 10, 'price': 500},   # $5.00
        'medium': {'credits': 50, 'price': 2000}, # $20.00
        'large': {'credits': 200, 'price': 5000}  # $50.00
    }
    
    pkg = packages[package]
    
    # Create Stripe Checkout Session
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f'{pkg["credits"]} AI Task Credits',
                },
                'unit_amount': pkg['price'],
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=f'{request.host_url}payment-success?session_id={{CHECKOUT_SESSION_ID}}',
        cancel_url=f'{request.host_url}payment-cancelled',
        metadata={
            'user_id': session['user_id'],
            'credits': pkg['credits']
        }
    )
    
    return jsonify({'checkout_url': checkout_session.url})

# Webhook to handle successful payments
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        return 'Invalid payload', 400
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']
        credits = int(session['metadata']['credits'])
        
        user = User.query.get(user_id)
        user.credits += credits
        
        CreditTransaction(
            user_id=user_id,
            amount=credits,
            type='purchase',
            stripe_payment_id=session['payment_intent']
        )
        db.session.commit()
    
    return jsonify({'status': 'success'})
```

**Option B: Alternative - Lemonsqueezy** (Even simpler, but takes ~3% more fees)

### Frontend Changes (Easy)

Add a credits display and purchase button:

```html
<!-- In index.html -->
<div class="credits-display">
    Credits: <span id="credit-count">0</span>
    <button onclick="openCreditsPurchase()">Buy More</button>
</div>

<div id="credits-modal" class="modal">
    <h3>Purchase Credits</h3>
    <div class="package" onclick="purchasePackage('small')">
        10 credits - $5
    </div>
    <div class="package" onclick="purchasePackage('medium')">
        50 credits - $20 (save 20%)
    </div>
    <div class="package" onclick="purchasePackage('large')">
        200 credits - $50 (save 50%)
    </div>
</div>
```

### Cost Structure Suggestion

Based on Claude Haiku 4.5 costs (~$0.03 per AI task parse):
- 10 credits = $5 (you keep ~$4.70 after Stripe fees)
- 50 credits = $20 (you keep ~$19)
- 200 credits = $50 (you keep ~$48.50)

### Critical Issues to Address

1. **Multi-user system**: Your current app uses single password. You'll need proper user accounts with username/password
2. **Migration path**: Give existing users free credits or grandfathered unlimited access
3. **Security**: Stripe webhooks must be validated to prevent credit fraud

### Recommended Approach

**Phase 1 (1 day):**
- Add User model with proper authentication (replace single APP_PASSWORD)
- Add credits column and transaction logging
- Gate `/api/tasks/parse` behind credit check

**Phase 2 (1 day):**
- Integrate Stripe Checkout
- Add purchase UI
- Test with Stripe test mode

**Phase 3 (0.5 day):**
- Add webhook handler for automatic credit grants
- Add admin panel to grant/revoke credits
- Monitor and adjust pricing

### Alternatives to Consider

1. **Subscription model** (simpler): $5/month unlimited vs pay-per-use
2. **Freemium**: 10 free credits/month, pay for more
3. **Just ask for donations** with optional $5/month Patreon-style support

**My recommendation**: Start with freemium (10 free/month) + Stripe Checkout for credit packs. This is the least friction and aligns with ADHD-friendly philosophy.

Want me to help implement any specific part?
