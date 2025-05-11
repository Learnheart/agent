def calculation(self, number):
    try:
        return eval(number)
    except Exception as e:
        return print(f"Error {e}")