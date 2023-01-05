from security import gen_assymetric_key, sign_message, verify_signature, gen_symmetric_key, encrypt_number, decrypt_number
import click

def test_sign_message():
    private_key, public_key = gen_assymetric_key()
    private_key_2, public_key_2 = gen_assymetric_key()
    message = b'This is a test message'
    message2 = b'This is another test message'
    signature = sign_message(message, private_key)
    signature_2 = sign_message(message, private_key_2)

    assert verify_signature(message, signature, public_key) == True
    assert verify_signature(message, signature_2, public_key) == False
    assert verify_signature(message, signature, public_key_2) == False
    assert verify_signature(message, signature_2, public_key_2) == True
    assert verify_signature(message2, signature, public_key) == False


def test_encrypt_number():
    symmetric_key = gen_symmetric_key()
    symmetric_key_2 = gen_symmetric_key()
    number = 42
    encrypted_number = encrypt_number(number, symmetric_key)
    encrypted_number_2 = encrypt_number(number, symmetric_key_2)
    decrypted_number = decrypt_number(encrypted_number, symmetric_key)
    decrypted_number_2 = decrypt_number(encrypted_number_2, symmetric_key_2)
    assert number == decrypted_number
    assert number == decrypted_number_2
    assert encrypted_number != encrypted_number_2


@click.command()
@click.option('--test', '-t', help='choose from: [sign_message]')
def main(test):
    if test == 'sign_message':
        test_sign_message()
    elif test == 'encrypt_number':
        test_encrypt_number()
    else:
        print("No test chosen")
        return
    print("All tests passed!")

if __name__ == "__main__":
    main()