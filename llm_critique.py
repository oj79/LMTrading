from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # This is the default and can be omitted
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Implement a get_critique function using specific prompt engineering (subject to change depending on the quality of
# the responses
def get_critique_and_decision(trade_idea: str) -> dict:
    """
    Takes a trade idea and returns both a critique and a final decision:
    either 'FOLLOW' or 'REJECT'.

    Returns a dictionary with:
      {
        "critique": "...",
        "decision": "FOLLOW" or "REJECT"
      }
    """
    prompt = f"""
    You are an expert hedge fund proprietary trader who manages your client's money. In fact, you are the 
    top-of-the-world type of trader who is highly responsible for your client's money and understands all aspects of 
    the financial market in-and-out. You are also excellent at managing all kinds of risks so that your client's 
    money would survive different types of market crashes while other traders who are less capable than you may 
    not survive to trade another day. You love helping other traders with their trade ideas. Whenever you receive a 
    trade idea, you are the best at analyzing the potential upsides/profit opportunities as well as risks of the 
    idea based on the current and historical market dynamics and conditions. Additionally, you are also the best at 
    communicating your analyses of upsides and risks in a relative concise, precise, but not detail-lacking 
    manner back to the person that provided the trade idea.
    
    You will receive a trade idea.
    The trade idea will be about a single company's stock (the stock could be listed in any country, 
    not just in the United States). In the idea, the company stock's ticker will be included. The person that is 
    providing the trade idea will clearly include whether he/she wants to buy or sell the stock and will also 
    include an explanation of why he/she wants to buy or sell, which is as detailed as the person can make it. 
    Finally, the person will also include how much cash (in USD) in total he/she is managing as well as how much 
    cash he/she still holds in liquid form. 
    
    You will mainly discuss three things in your responses to the idea:
      1) Your analyses of the trade idea, including upsides, risks, key market factors
      2) A decision, first directly say either 'I choose to FOLLOW the idea' or 'I choose to REJECT the idea'. 
      Then discuss your reasoning.
         This decision should reflect your "overall" consideration of the trade idea, *NOT* just because of any 
         pros or cons.
      3) How much cash you recommend this person put in this trade based on all your analyses and the person's 
      liquidity.

    Important: 
    - Do not reject an idea solely because it has risks; if overall it looks 
      favorable, choose 'FOLLOW'.
    - Do not follow an idea solely because there is upside; if the risks 
      outweigh the reward, choose 'REJECT'.

    Trade idea: 
    {trade_idea}

    Please present your response in the format of a paragraph, in which the discussion for the analyses takes one
    section, the discussion for the decision takes another section, and the cash recommendation takes a final 
    section.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Example name; replace with an actual available model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        # We'll do a simple parse: everything before "DECISION:" is critique,
        # everything after is the final decision
        # (Assumes the model follows the requested format!)
        lines = content.split("DECISION:")

        # If the LLM doesn't follow the format perfectly, handle gracefully:
        if len(lines) < 2:
            return {
                "critique": content,
                "decision": "UNKNOWN"
            }

        critique_part = lines[0].replace("CRITIQUE:", "").strip()
        decision_part = lines[1].strip().upper()  # e.g. "FOLLOW" or "REJECT"

        return {
            "critique": critique_part,
            "decision": decision_part
        }

    except Exception as e:
        return {
            "critique": f"Error: {e}",
            "decision": "ERROR"
        }