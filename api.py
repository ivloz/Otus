#!/usr/bin/env python3

import random
import json
import datetime
import logging
import hashlib
import uuid

from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

from scoring import get_score

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class ValidationError(Exception):
    pass


class FieldDescriptor:
    def __init__(self, name=None):
        self.name = name

    def __get__(self, instance, owner):
        return instance.__dict__.get(self.name, None)

    def __set__(self, instance, value):
        self._validate(instance, value)
        instance.__dict__[self.name] = value

    def _validate(self, instance, value):
        pass


class StructureMeta(type):
    def __new__(_type, name, bases, attrs):
        _fields = []
        for attr_name, attr in attrs.items():
            if isinstance(attr, FieldDescriptor):
                attrs[attr_name].name = attr_name
                _fields.append(attr)
        cls = super().__new__(_type, name, bases, attrs)
        cls._fields = _fields

        return cls


class Structure(metaclass=StructureMeta):
    def __init__(self, **fields):
        self.filled_fields = []
        self.errors = {}
        self.not_empty_fields = []

        for field_name, field_value in fields.items():
            try:
                setattr(self, field_name, field_value)
            except ValidationError as e:
                self.errors[field_name] = str(e)
            self.filled_fields.append(field_name)
            if field_value:
                self.not_empty_fields.append(field_name)
        self._validate()

    def _validate(self):
        for field in self._fields:
            if field.required and field.name not in self.filled_fields:
                self.errors.update({field.name: "field is required, but not filled"})


class TypedField(FieldDescriptor):
    type = object

    def __set__(self, instance, value):
        if not isinstance(value, self.type):
            raise ValidationError("Value {} has not suitable type ({})".format(value, self.type))
        super().__set__(instance, value)


class RequiredField(FieldDescriptor):
    def __init__(self, *args, required=False, **kwargs):
        self.required = required
        super().__init__(*args, **kwargs)


class NullableField(FieldDescriptor):
    def __init__(self, *args, nullable=False, **kwargs):
        self.nullable = nullable
        super().__init__(*args, **kwargs)

    def _validate(self, instance, value):
        super()._validate(instance, value)
        if not value and not self.nullable:
            raise ValidationError("Field {} should not be nullable".format(self.name))


class CharField(TypedField, RequiredField, NullableField):
    type = str


class DictField(TypedField, RequiredField, NullableField):
    type = dict


class DateField(RequiredField, NullableField):
    def _validate(self, instance, value):
        super()._validate(instance, value)
        try:
            datetime.datetime.strptime(value, '%d.%m.%Y')
        except ValueError:
            raise ValidationError("Wrong date format")


class ArgumentsField(DictField):
    pass


class EmailField(CharField):
    def _validate(self, instance, value):
        super()._validate(instance, value)
        if value is None:
            return
        if "@" not in value:
            raise ValidationError("Email {} has wrong format".format(self.name))


class PhoneField(RequiredField, NullableField):
    def _validate(self, instance, value):
        super()._validate(instance, value)
        if value is None:
            return
        if not isinstance(value, int) and not isinstance(value, str):
            raise ValidationError("Wrong phone string type")
        if len(str(value)) != 11:
            raise ValidationError("Phone should has length equal to 11")
        if not str(value).startswith("7"):
            raise ValidationError("Phone should be started from 7")


class BirthDayField(DateField, RequiredField, NullableField):
    def _validate(self, instance, value):
        super()._validate(instance, value)
        if value is None:
            return
        date = datetime.datetime.strptime(value, '%d.%m.%Y')
        delta = datetime.datetime.now().year - date.year
        if delta > 70 or delta <= 0:
            raise ValidationError("Wrong birth day")


class GenderField(TypedField, RequiredField, NullableField):
    type = int

    def _validate(self, instance, value):
        super()._validate(instance, value)
        if value is None:
            return
        if value not in GENDERS:
            raise ValidationError("Wrong gender value")


class ClientIDsField(TypedField, RequiredField, NullableField):
    type = list

    def _validate(self, instance, value):
        super()._validate(instance, value)
        for _id in value:
            if not isinstance(_id, int):
                raise ValidationError("Some item in client_ids has not int type")


class ClientsInterestsRequest(Structure):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    @staticmethod
    def get_interests():
        interests = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus"]
        return random.sample(interests, 2)

    def _interests(self):
        interests = {}
        for client_id in self.client_ids:
            interests[client_id] = self.get_interests()
        return interests


class OnlineScoreRequest(Structure):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def _validate(self):
        super()._validate()
        valid_pairs = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("gender", "birthday")
        ]
        if self.gender == 0:
            self.not_empty_fields.append("gender")
        valid = False
        for pair in valid_pairs:
            if all(field in self.not_empty_fields for field in pair):
                valid = True
                break
        if not valid:
            self.errors["pairs"] = "No valid filed pairs"


class MethodRequest(Structure):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512((datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode("utf-8")).hexdigest()
    else:
        digest = hashlib.sha512((request.account + request.login + SALT).encode("utf-8")).hexdigest()
    if digest == request.token:
        return True
    return False


def online_score_handler(ctx, params):
    score_request = OnlineScoreRequest(**params.arguments)
    if score_request.errors:
        return score_request.errors, INVALID_REQUEST
    ctx["has"] = score_request.not_empty_fields

    if params.is_admin:
        score = 42
    else:
        score = get_score(store=None,
                          phone=score_request.phone,
                          email=score_request.email,
                          birthday=score_request.birthday,
                          gender=score_request.birthday,
                          first_name=score_request.first_name,
                          last_name=score_request.last_name
                          )

    return {"score": score}, OK


def clients_interests_handler(ctx, params):
    interests_request = ClientsInterestsRequest(**params.arguments)
    if interests_request.errors:
        return interests_request.errors, INVALID_REQUEST
    ctx["nclients"] = len(interests_request.client_ids)
    return interests_request._interests(), OK


def method_handler(request, ctx, store):
    method_handlers = {
        "online_score": online_score_handler,
        "clients_interests": clients_interests_handler
    }
    if "body" not in request:
        return "Request do not contain 'body'", BAD_REQUEST

    validated_params = MethodRequest(**request["body"])

    if validated_params.errors:
        return validated_params.errors, INVALID_REQUEST

    if not check_auth(validated_params):
        return "Forbidden", FORBIDDEN

    method = request['body'].get("method", "")
    if method not in method_handlers:
        return "Call nonexistent method", NOT_FOUND
    response, code = method_handlers[method](ctx, validated_params)

    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            data_string = data_string.decode("utf-8")
            request = json.loads(data_string)
        except Exception as e:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write((json.dumps(r)).encode("utf-8"))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
