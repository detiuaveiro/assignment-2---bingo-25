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
        # Generate two symmetric keys
    sym_key1 = gen_symmetric_key()
    sym_key2 = gen_symmetric_key()
    sym_key3 = gen_symmetric_key()
    sym_key4 = gen_symmetric_key()
    sym_key5 = gen_symmetric_key()
    
    # Encrypt and decrypt the number
    number = 42

    encrypted_once = encrypt_number(number, sym_key1)
    encrypted_twice = encrypt_number(encrypted_once, sym_key2)
    encrypted_thrice = encrypt_number(encrypted_twice, sym_key3)
    encrypted_four_times = encrypt_number(encrypted_thrice, sym_key4)
    encrypted_five_times = encrypt_number(encrypted_four_times, sym_key5)

    decrypt_five_times = decrypt_number(encrypted_five_times, sym_key5)
    decrypt_four_times = decrypt_number(decrypt_five_times, sym_key4)
    decrypt_thrice = decrypt_number(decrypt_four_times, sym_key3)
    decrypt_twice = decrypt_number(decrypt_thrice, sym_key2)
    decrypt_once = decrypt_number(decrypt_twice, sym_key1, 1)

    assert decrypt_five_times == encrypted_four_times
    assert decrypt_four_times == encrypted_thrice
    assert decrypt_thrice == encrypted_twice
    assert decrypt_twice == encrypted_once
    assert number == decrypt_once


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