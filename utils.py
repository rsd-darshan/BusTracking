from werkzeug.utils import secure_filename

def custom_secure_filename(filename):
    return secure_filename(filename)
