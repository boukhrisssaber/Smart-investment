from load_model import model, X_train, y_train

score = model.evaluate(X_train, y_train, verbose=0)
print (score)