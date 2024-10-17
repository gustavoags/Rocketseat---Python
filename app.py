from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = "minha_chave_123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'

#! GERENCIAMENTO DE SESSÃO DE USUÁRIO
login_manager = LoginManager()
db = SQLAlchemy(app) # Linkando com o BD
login_manager.init_app(app)
login_manager.login_view = 'login'
CORS(app)


#! MODELAGEM

#? User (id, username, password)
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    cart = db.relationship('CartItem', backref='user', lazy=True)

#? Produto (id, name, price, description); Adicionando as colunas do produto
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

#? Carrinho
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    
#! AUTENTICAÇÃO

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#! ROTAS

#? Rota para Logar
@app.route('/login', methods=["POST"]) 
def login():
    data = request.json
    
    user = User.query.filter_by(username=data.get("username")).first() #Filtrar uma coluna
    
    if user and data.get("password") == user.password: 
        login_user(user)
        return jsonify({"message": "Logged in successfully"})
    
    return jsonify({"message": "Unauthorized. Invalid credentials"})

#? Rota para LogOut
@app.route('/logout', methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successfully"})

#? Rota para adicionar um Produto
@app.route('/api/products/add', methods=["POST"])
@login_required 
def add_product():
    data = request.json #receber os dados da requisição
    if 'name' in data and 'price' in data: # Verificando se há nome e preco do produto
        product = Product(name=data["name"],price=data["price"],description=data.get("description", ""))
        db.session.add(product) # Adicionando os valores do produto
        db.session.commit() # Comitando(postando) os valores no BD
        return jsonify({"message": "Product add successfully"})
    return jsonify({"message": "Invalid product data"}), 400 # A resposta tem que ser em JSON por isso usamos a biblioteca jsonify(); 400 é erro

#? Rota para deletar um produto
@app.route('/api/products/delete/<int:product_id>', methods=["DELETE"])
@login_required
def delete_product(product_id):
    product = Product.query.get(product_id)
    if product:
        db.session.delete(product) #deletando
        db.session.commit()
        return jsonify({"message": "Product deleted successfully"})
    return jsonify({"message": "Product not found"}), 404

@app.route('/api/products/<int:product_id>', methods=["GET"]) # GET é usado para recuperar informação
def get_products_details(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify({
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description
        })
    return jsonify({"message": "Product not found"}), 404

#? Rota para atualizar o produto
@app.route('/api/products/update/<int:product_id>', methods=["PUT"]) 
@login_required 
def update_products(product_id):
    product = Product.query.get(product_id)
    if not product: # Verificando se o produto e existe; não foi encontrado
        return jsonify({"message": "Product not found"})
    
    data = request.json # Requerindo os dados
    if "name" in data: # Se o nome do produto está no BD fará o seguinte...
        product.name = data['name'] # Alterando o nome do produto
    
    if "price" in data:
        product.price = data['price']
        
    if "description" in data:
        product.description = data['description']
    
    db.session.commit()
    return jsonify({"message": "Product update successfully"})

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    product_list = []
    for product in products:
        product_data = {
            "id": product.id,
            "name": product.name,
            "price": product.price
        }
        product_list.append(product_data)
    return jsonify(product_list)   

#? Checkout

#? Rota para adicionar os itens no carrinho
@app.route('/api/cart/add/<int:product_id>', methods=["POST"])
@login_required
def add_to_cart(product_id):
    # Usuário
    user = User.query.get(int(current_user.id))
    # Produto
    product = Product.query.get(product_id)

    if user and product:
        cart_item = CartItem(user_id=user.id, product_id=product.id)
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"message": "Item added to the cart successfully"})
    return jsonify({"message": "Failed to add item to the cart"}), 400 
 
#? Rota para deletar o item do carrinho
@app.route('/api/cart/remove/<int:product_id>', methods=["DELETE"])
@login_required
def remove_from_cart(product_id):
    # Produto, Usuário = Item no Carrinho
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Item removed from the cart successfully"})
    return jsonify({"message": "Failed to remove item from the cart"})

#? Rota para vizualizar os produtos que estão no carrinhi
@app.route('/api/cart', methods=["GET"])
@login_required
def view_cart():
    # Usuário
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    cart_content = [] # Criando uma lista dos produtos no carrinho
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)   
        cart_content.append({
                            "id": cart_item.id,
                            "user_id": cart_item.user_id,
                            "product_id": cart_item.product_id,
                            "product_name": product.name,
                            "product_price": product.price
        })
    return jsonify(cart_content)

#? Rota para limpar o carrinho
@app.route('/api/cart/checkout', methods=["POST"])
@login_required
def checkout():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    for cart_item in cart_items:
        db.session.delete(cart_item)
    db.session.commit()
    return jsonify({"message":"Checkout successful. Cart has been cleared."})



if __name__ == "__main__":
    app.run(debug=True)