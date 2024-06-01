
import openai

openai.api_key = 'sk-proj-3f0FxEOzv6YjWxUhhDnWT3BlbkFJDEfwBaRWesQxQ3vyzaFc'

usage = openai.Usage.retrieve()
print("Usage:", usage)