import base64
import PyKCS11
from cryptography import x509
from cryptography.hazmat.backends import default_backend as db
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.hashes import SHA1, Hash


def get_cert_data():
    """ get certificate data from card
    :return: certificate data
    """
    lib = '/usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so'
    pkcs11 = PyKCS11.PyKCS11Lib()
    pkcs11.load(lib)
    slot = pkcs11.getSlotList(tokenPresent=True)[0]
    session = pkcs11.openSession(slot)
    cert_obj = session.findObjects([
                  (PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE),
                  (PyKCS11.CKA_LABEL, 'CITIZEN AUTHENTICATION CERTIFICATE')
                  ])[0]

    cert_der_data = bytes(cert_obj.to_dict()['CKA_VALUE'])
    session.closeSession()
    return cert_der_data.hex()


def sign_message(text):
    """ sign message with card 
    :param text: text to sign
    :return: signature
    """
    text = text.__repr__().encode('utf-8')
    lib = '/usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so'
    pkcs11 = PyKCS11.PyKCS11Lib()
    pkcs11.load(lib)
    slot = pkcs11.getSlotList(tokenPresent=True)[0]
    session = pkcs11.openSession(slot, PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
    session.login('1111')
    criteria = [(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY), (PyKCS11.CKA_KEY_TYPE, PyKCS11.CKK_RSA), (PyKCS11.CKA_LABEL, 'CITIZEN AUTHENTICATION KEY' )]
    keys = session.findObjects(criteria)
    key = keys[0]
    mechanism = PyKCS11.Mechanism(PyKCS11.CKM_SHA1_RSA_PKCS, None)
    signature = bytes(session.sign(key=key,data=text, mecha=mechanism))
    session.logout()
    session.closeSession()
    return signature.hex()

def validate_signature(signature, text, cert_der_data):
    """ validate signature with certificate
    :param signature: signature to validate
    :param text: text to validate
    :param cert_der_data: certificate data
    :return: True if signature is valid, False otherwise
    """
    cert_der_data = bytes.fromhex(cert_der_data)
    signature = bytes.fromhex(signature)
    text = text.__repr__().encode('utf-8')

    cert = x509.load_der_x509_certificate(cert_der_data, db())
    md = Hash(SHA1(), backend=db())
    md.update(text)
    digest = md.finalize()

    public_key = cert.public_key()
    try:
        public_key.verify(signature, digest, PKCS1v15(), SHA1())
        return True
    except:
        return False

def get_name_and_number(cert_data):
    """ get name and citizen number from certificate
    :param cert_data: certificate data
    :return: name and citizen number
    """
    cert_data = bytes.fromhex(cert_data)
    cert = x509.load_der_x509_certificate(cert_data, db())
    name  = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    citizen_number = cert.subject.get_attributes_for_oid(x509.NameOID.SERIAL_NUMBER)[0].value
    return name, citizen_number

def main():
    text = b'text to sign'
    cert_der_data = get_cert_data()
    encoded_cert = base64.b64encode(cert_der_data)
    print(encoded_cert)
    print(encoded_cert.decode('utf-8'))
    # signature = sign_message(text)
    # print(validate_signature(signature, text, cert_der_data))
    # print(get_name_and_number(cert_der_data))    

if __name__ == '__main__':
    main()
