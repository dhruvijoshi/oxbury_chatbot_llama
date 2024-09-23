from flask import Flask, render_template, request, jsonify
import requests
import spacy
import re
import os
import ollama

api_key = os.getenv('COMPANY_HOUSE_API')

retrieved_data = {}
app = Flask(__name__)

@app.route("/")
def index():
    return render_template('main.html')

@app.route("/generate", methods=["POST"])
def generate():
    # Fetching inputs from user
    msg = request.form["msg"]
    nlp = spacy.load("en_core_web_sm")
    msg = nlp(msg)
   
    # Regex to find postcode in input
    postcode_pattern = r'\b[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][ABD-HJLNP-UW-Z]{2}\b'
    c_postcode = re.findall(postcode_pattern, msg.text)
    
    if c_postcode:
        # Call API using postcode
        response = call_using_add(c_postcode)
        return response
    
    # Searching company name or number from input 
    for token in msg:
        if (token.pos_ == 'PROPN' and token.is_alpha == True) or (token.pos_ == 'PROPN' and token.ent_type_ == 'ORG'):
            response = call_using_name(token.text)
            return response

        if token.pos_ == 'NUM' and len(token.text) == 8:
            print(f'calling call_using_number fuction {token.text}')
            response = call_using_number(token.text)
            return response
    
    # Ollama call if no match
    response = generate_text(msg.text)
    return response


# Generates output for the chatbot
def generate_text(prompt, max_length=100):
    result = []
   
    # If company data is retrieved from API
    if retrieved_data:
        
        print(f'prompt passed in generate_text if block {prompt}')
        print(f'retrieved data is {retrieved_data}')
        for value in retrieved_data.values():
            company_name = value.get('name', 'N/A')
            company_number = value.get('number', 'N/A')
            company_address = value.get('address', 'N/A')

            generated_text = (
                f"<br>Company: {company_name}<br>"
                f"Number: {company_number}<br>"
                f"Location: {company_address}<br>"
            )
            result.append(generated_text)

        retrieved_data.clear()
        return ''.join(result)
    
    # Generates output for queries other than Company details
    else:
        result = ollama.chat(model='llama3.1', messages=[
            {
                'role': 'system',
                'content': 'You are a chatbot for a bank. You have to give information about the company user asked about. Keep your answer brief'
        },
        {
            'role': 'user',
            'content': prompt
        },
        ])
        return jsonify(result['message']['content'])


# Will be called if there is company name in the input
def call_using_name(name):
    # Fetching data from API
    url = f'https://api.company-information.service.gov.uk/search/companies?q={name}'
    response = requests.get(url, auth=(api_key, ''))
    data = response.json()    
    
    if response.status_code != 200 or 'items' not in data:
        answer = generate_text(data)
        return answer

    # Extracting useful information from API response
    i = 0
    for item in data['items']:
        i +=1
        company_number = item['company_number']
        company_name = item['title']
        address = item.get('address', {})
        premises = address.get('premises', '')
        address_line_1 = address.get('address_line_1', '')
        locality = address.get('locality', '')
        postal_code = address.get('postal_code', '')
        
        full_address = f"{premises} {address_line_1}, {locality}, {postal_code}".strip()
        
        retrieved_data[i] = {'name': company_name, 'number': company_number, 'address': full_address}
    
    answer = generate_text(retrieved_data)
    return answer


# Will be called if there is company number in the input
def call_using_number(c_num):
    # Fetching data from API
    url = f'https://api.company-information.service.gov.uk/search?q={c_num}'
    response = requests.get(url, auth=(api_key, ''))
    data = response.json()
    
    if response.status_code != 200:
        answer = generate_text(data)
        return answer
    
    # Extracting useful information from API response
    for item in data['items']:
        company_number = item['company_number']
        company_name = item['title']
        address = item.get('address', {})
        premises = address.get('premises', '')
        address_line_1 = address.get('address_line_1', '')
        locality = address.get('locality', '')
        postal_code = address.get('postal_code', '')
        
        full_address = f"{premises} {address_line_1}, {locality}, {postal_code}".strip()
        retrieved_data[1] = {'name' : company_name, 'number' : company_number, 'address' : full_address}
    
    answer = generate_text(retrieved_data)
    return answer


# Will be called if there is company's postcode in the input
def call_using_add(c_add):
    # Fetching data from API
    url = f'https://api.company-information.service.gov.uk/search?q={c_add}'
    response = requests.get(url, auth=(api_key, ''))
    data = response.json()

    if response.status_code != 200:
        answer = generate_text(data)
        return answer
    
    # Extracting useful information from API response
    i = 0
    for item in data['items']:
        if item['kind'] == 'searchresults#company':
            i += 1
            company_name = item['title']
            address = item.get('address', {})
            premises = address.get('premises', '')
            address_line_1 = address.get('address_line_1', '')
            locality = address.get('locality', '')
            postal_code = address.get('postal_code', '')
            company_number = item['company_number']

            full_address = f"{premises} {address_line_1}, {locality}, {postal_code}".strip()
            retrieved_data[i] = {'name' : company_name, 'number' : company_number, 'address' : full_address}

    answer = generate_text(retrieved_data)
    return answer


if __name__ == '__main__':
    app.run()
