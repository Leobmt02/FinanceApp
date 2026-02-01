"""
FinanceApp Frontend - Flask + HTMX + Tailwind
Mobile-first personal finance management app.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import requests
import os
import sys
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# Backend API URL
API_URL = os.getenv("API_URL", "http://localhost:8000/api")
print(f"[STARTUP] API_URL = {API_URL}", file=sys.stderr, flush=True)


# ============================================
# HELPERS
# ============================================

def get_auth_headers():
    """Get authorization headers with JWT token."""
    token = session.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_request(method, endpoint, data=None, params=None):
    """Make authenticated request to the backend API."""
    url = f"{API_URL}{endpoint}"
    headers = get_auth_headers()
    headers["Content-Type"] = "application/json"
    
    # Debug: print token status
    print(f"[DEBUG] API Request to {url}", file=sys.stderr, flush=True)
    print(f"[DEBUG] Token in session: {'Yes' if session.get('access_token') else 'No'}", file=sys.stderr, flush=True)
    
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=headers,
            timeout=10
        )
        print(f"[DEBUG] Response status: {response.status_code}", file=sys.stderr, flush=True)
        return response
    except requests.RequestException as e:
        print(f"[DEBUG] Request error: {e}", file=sys.stderr, flush=True)
        return None


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "access_token" not in session:
            flash("Por favor, faça login para continuar.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# AUTH ROUTES
# ============================================

@app.route("/")
def index():
    """Redirect to dashboard or login."""
    if "access_token" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")
        
        # OAuth2 expects form-urlencoded with username/password
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": email, "password": senha},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            session["access_token"] = token
            
            # Get user info using the token directly
            user_response = requests.get(
                f"{API_URL}/auth/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            if user_response.status_code == 200:
                session["user"] = user_response.json()
            
            flash("Login realizado com sucesso!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Email ou senha incorretos.", "error")
    
    return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Registration page."""
    if request.method == "POST":
        data = {
            "nome": request.form.get("nome"),
            "email": request.form.get("email"),
            "celular": request.form.get("celular"),
            "senha": request.form.get("senha"),
            "confirmar_senha": request.form.get("confirmar_senha")
        }
        
        response = requests.post(
            f"{API_URL}/auth/register",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect(url_for("login"))
        else:
            try:
                error_data = response.json()
                error = error_data.get("detail", "Erro ao criar conta")
            except Exception:
                error = f"Erro ao criar conta (status {response.status_code})"
            flash(error, "error")
    
    return render_template("auth/register.html")


@app.route("/logout")
def logout():
    """Logout and clear session."""
    session.clear()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("login"))


# ============================================
# DASHBOARD ROUTES
# ============================================

@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard page."""
    from datetime import datetime
    
    mes = request.args.get("mes", datetime.now().month, type=int)
    ano = request.args.get("ano", datetime.now().year, type=int)
    
    # Get dashboard summary
    summary_response = api_request("GET", "/dashboard/summary", params={"mes": mes, "ano": ano})
    summary = summary_response.json() if summary_response and summary_response.status_code == 200 else {}
    
    # Get expenses by category
    categories_response = api_request("GET", "/dashboard/categories", params={"mes": mes, "ano": ano})
    categories = categories_response.json() if categories_response and categories_response.status_code == 200 else {}
    
    # Get recent transactions
    recent_response = api_request("GET", "/dashboard/recent-transactions", params={"limit": 5})
    recent_transactions = recent_response.json() if recent_response and recent_response.status_code == 200 else []
    
    # Get savings summary
    savings_response = api_request("GET", "/dashboard/savings-summary")
    savings = savings_response.json() if savings_response and savings_response.status_code == 200 else {}
    
    return render_template(
        "dashboard/index.html",
        summary=summary,
        categories=categories,
        recent_transactions=recent_transactions,
        savings=savings,
        mes=mes,
        ano=ano,
        user=session.get("user", {})
    )


# ============================================
# TRANSACTIONS ROUTES
# ============================================

@app.route("/transactions")
@login_required
def transactions():
    """Transactions list page."""
    tipo = request.args.get("tipo")
    categoria = request.args.get("categoria")
    
    params = {}
    if tipo:
        params["tipo"] = tipo
    if categoria:
        params["categoria"] = categoria
    
    response = api_request("GET", "/transactions/", params=params)
    transactions_list = response.json() if response and response.status_code == 200 else []
    
    # Get categories for filter
    cat_response = api_request("GET", "/transactions/categories")
    categories = cat_response.json() if cat_response and cat_response.status_code == 200 else []
    
    return render_template(
        "transactions/list.html",
        transactions=transactions_list,
        categories=categories,
        user=session.get("user", {})
    )


@app.route("/transactions/new", methods=["GET", "POST"])
@login_required
def new_transaction():
    """Create new transaction."""
    if request.method == "POST":
        data = {
            "valor_total": float(request.form.get("valor_total", 0)),
            "descricao": request.form.get("descricao"),
            "categoria": request.form.get("categoria"),
            "tipo": request.form.get("tipo"),
            "data_compra": request.form.get("data_compra"),
            "num_parcelas": int(request.form.get("num_parcelas", 1)),
            "notas": request.form.get("notas")
        }
        
        response = api_request("POST", "/transactions/", data=data)
        
        if response and response.status_code == 201:
            flash("Transação criada com sucesso!", "success")
            
            # If HTMX request, return redirect header
            if request.headers.get("HX-Request"):
                resp = jsonify({"success": True})
                resp.headers["HX-Redirect"] = url_for("transactions")
                return resp
            
            return redirect(url_for("transactions"))
        else:
            error = response.json().get("detail", "Erro ao criar transação") if response else "Erro de conexão"
            flash(error, "error")
    
    return render_template("transactions/form.html", user=session.get("user", {}))


@app.route("/transactions/<int:id>/delete", methods=["DELETE", "POST"])
@login_required
def delete_transaction(id):
    """Delete a transaction."""
    response = api_request("DELETE", f"/transactions/{id}")
    
    if response and response.status_code == 204:
        flash("Transação excluída!", "success")
    else:
        flash("Erro ao excluir transação.", "error")
    
    if request.headers.get("HX-Request"):
        return "", 200
    
    return redirect(url_for("transactions"))


# ============================================
# SAVINGS ROUTES
# ============================================

@app.route("/savings")
@login_required
def savings():
    """Savings goals list page."""
    response = api_request("GET", "/savings/")
    goals = response.json() if response and response.status_code == 200 else []
    
    return render_template(
        "savings/list.html",
        goals=goals,
        user=session.get("user", {})
    )


@app.route("/savings/new", methods=["GET", "POST"])
@login_required
def new_savings_goal():
    """Create new savings goal."""
    if request.method == "POST":
        data = {
            "nome_objetivo": request.form.get("nome_objetivo"),
            "descricao": request.form.get("descricao"),
            "valor_meta": float(request.form.get("valor_meta", 0)),
            "valor_inicial": float(request.form.get("valor_inicial", 0)),
            "data_limite": request.form.get("data_limite") or None
        }
        
        response = api_request("POST", "/savings/", data=data)
        
        if response and response.status_code == 201:
            flash("Meta criada com sucesso!", "success")
            return redirect(url_for("savings"))
        else:
            flash("Erro ao criar meta.", "error")
    
    return render_template("savings/form.html", user=session.get("user", {}))


@app.route("/savings/<int:id>/deposit", methods=["POST"])
@login_required
def deposit_savings(id):
    """Deposit into savings goal."""
    valor = float(request.form.get("valor", 0))
    
    response = api_request("POST", f"/savings/{id}/deposit", data={"valor": valor})
    
    if response and response.status_code == 200:
        flash(f"R$ {valor:.2f} depositado com sucesso!", "success")
    else:
        flash("Erro ao depositar.", "error")
    
    if request.headers.get("HX-Request"):
        # Return updated goal card
        goal = response.json() if response else {}
        return render_template("savings/_goal_card.html", goal=goal)
    
    return redirect(url_for("savings"))


@app.route("/savings/<int:id>/withdraw", methods=["POST"])
@login_required
def withdraw_savings(id):
    """Withdraw from savings goal."""
    valor = float(request.form.get("valor", 0))
    
    response = api_request("POST", f"/savings/{id}/withdraw", data={"valor": valor})
    
    if response and response.status_code == 200:
        flash(f"R$ {valor:.2f} resgatado com sucesso!", "success")
    else:
        error = response.json().get("detail", "Erro ao resgatar") if response else "Erro"
        flash(error, "error")
    
    return redirect(url_for("savings"))


# ============================================
# REPORTS ROUTES
# ============================================

@app.route("/reports/monthly")
@login_required
def monthly_report():
    """Monthly financial report page."""
    from datetime import datetime, date
    import calendar
    
    mes = request.args.get("mes", datetime.now().month, type=int)
    ano = request.args.get("ano", datetime.now().year, type=int)
    
    # Get summary cards
    summary_response = api_request("GET", "/dashboard/summary", params={"mes": mes, "ano": ano})
    summary = summary_response.json() if summary_response and summary_response.status_code == 200 else {}
    
    # Get categories breakdown
    categories_response = api_request("GET", "/dashboard/categories", params={"mes": mes, "ano": ano})
    categories = categories_response.json() if categories_response and categories_response.status_code == 200 else {}
    
    # Get transactions for the month
    # Calculate start and end date of the month
    last_day = calendar.monthrange(ano, mes)[1]
    data_inicio = date(ano, mes, 1).isoformat()
    data_fim = date(ano, mes, last_day).isoformat()
    
    # We need a transactions endpoint that supports date filtering
    # The current transactions list endpoint supports filters, let's use it
    transactions_response = api_request("GET", "/transactions/", params={
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "page_size": 100 
    })
    transactions = transactions_response.json() if transactions_response and transactions_response.status_code == 200 else []
    
    return render_template(
        "reports/monthly.html",
        summary=summary,
        categories=categories,
        transactions=transactions,
        mes=mes,
        ano=ano,
        user=session.get("user", {})
    )


# ============================================
# HTMX PARTIALS
# ============================================

@app.route("/partials/dashboard-summary")
@login_required
def partial_dashboard_summary():
    """HTMX partial for dashboard summary."""
    from datetime import datetime
    
    mes = request.args.get("mes", datetime.now().month, type=int)
    ano = request.args.get("ano", datetime.now().year, type=int)
    
    response = api_request("GET", "/dashboard/summary", params={"mes": mes, "ano": ano})
    summary = response.json() if response and response.status_code == 200 else {}
    
    return render_template("dashboard/_summary.html", summary=summary)


# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)
