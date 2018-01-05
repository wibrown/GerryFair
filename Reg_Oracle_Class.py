# regression oracle class
# b0 and b1 are regression objects from the class linear_model
class RegOracle:
    def __init__(self, b0, b1):
        self.b0 = b0
        self.b1 = b1

    def predict(self, X):
        reg0 = self.b0
        reg1 = self.b1
        n = X.shape[0]
        y = []
        for i in range(n):
            x_i = X.iloc[i, :]
            x_i = x_i.values.reshape(1, -1)
            c_0 = reg0.predict(x_i)
            c_1 = reg1.predict(x_i)
            y_i = int(c_1 < c_0)
            y.append(y_i)
        return y
