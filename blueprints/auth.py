import datetime
from pydantic import ValidationError
from sqlalchemy import exc
from flask import jsonify, make_response
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from flask_openapi3 import APIBlueprint, Tag

from utils.utils import format_error
from models import Session
from models.usuario import Usuario
from schemas.error import ErrorSchema
from schemas.usuario import (
    UsuarioLoginSchema,
    UsuarioRegisterSchema,
    UsuarioViewSchema,
    apresenta_usuario,
)

usuario_tag = Tag(
    name="Usuario", description="Adição, visualização e remoção de usuários à base"
)
# security = [{"jwt": []}]
security = [{"api_key": []}]


bp = APIBlueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    abp_tags=[usuario_tag],
    abp_security=security,
    abp_responses={"400": ErrorSchema, "409": ErrorSchema},
    doc_ui=True,
)


@bp.post("/register", responses={"200": UsuarioViewSchema})
def cadastro_usuario(form: UsuarioRegisterSchema):
    """Adiciona um novo usuário a base de dados

    Retorna uma representação do usuário omitindo a senha.
    """
    nome = form.name
    email = form.email
    senha = form.password

    novo_usuario = Usuario(nome=nome, email=email, senha=senha)

    try:
        # criando conexão com a base
        session = Session()
        # adicionando novo usuário
        session.add(novo_usuario)
        # efetivando o camando de adição de novo item na tabela
        session.commit()
        return apresenta_usuario(novo_usuario), 200

    except exc.IntegrityError:
        session.rollback()
        # como a duplicidade do nome é a provável razão do IntegrityError
        error_msg = "Usuário já cadastrado com esse email :/"
        return jsonify(format_error(error_msg)), 409

    except Exception:
        # caso um erro fora do previsto
        error_msg = "Não foi possível salvar novo usuário :/"
        return jsonify(format_error(error_msg)), 400


@bp.post("/login", responses={"200": UsuarioViewSchema})
def login(form: UsuarioLoginSchema):
    email = form.email
    senha = form.password

    session = Session()
    usuario = session.query(Usuario).filter_by(email=email).first()

    if usuario and usuario.checa_senha(senha):
        # cria um token de acesso
        access_token = create_access_token(
            identity=email, expires_delta=datetime.timedelta(minutes=600)
        )
        # cria uma resposta com o token
        resposta = make_response(jsonify({"message": "Login successful"}))
        # adiciona as infomações necessárias no cookie
        set_access_cookies(resposta, access_token)
        # resposta.set_cookie("acess_token", access_token)
        # resposta.set_cookie("nome_usuario", usuario.nome)
        # retorna o token de acesso
        return resposta, 200
    else:
        # caso um erro fora do previsto
        error_msg = "Senha ou email não encontrado no sistema :/"
        return jsonify(format_error(error_msg)), 400


@bp.get("/quemeusou", responses={"200": UsuarioViewSchema})
@jwt_required()
def get_dado_secao():
    """
    Retorna uma representação do usuário que está logado no sistema.
    """
    current_user = get_jwt_identity()
    if current_user:
        session = Session()
        usuario = session.query(Usuario).filter_by(email=current_user).first()
        return apresenta_usuario(usuario), 200


@bp.post("/logout")
def logout():
    resp = jsonify({"logout": True})
    unset_jwt_cookies(resp)
    return resp, 200
