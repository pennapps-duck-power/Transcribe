all:
	zip -r transcribe.zip lib/python3.6/site-packages
	zip -g transcribe.zip lambda_function.py
