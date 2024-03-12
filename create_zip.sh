#!/bin/bash

# Navigate to the "package" directory
cd package

# Zip the contents of the "package" directory
zip -r ../lambda_function.zip .

# Navigate back to the parent directory
cd ..

# Add the "lambda_function.py" file to the existing zip file
zip -g lambda_function.zip lambda_function.py

# Print a message indicating the completion
echo "Zip file 'lambda_function.zip' created successfully."
