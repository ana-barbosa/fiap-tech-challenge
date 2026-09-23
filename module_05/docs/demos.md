# Demos

This file contains recorded demos from this application.

**Notes:**
- Videos were trimmed to reduce file size and viewing time, but the full functionality is reproducible with the code.
- Telegram doesn't allow hyperlinks that aren't publicly hosted (e.g. `http://localhost:8000`), so there are no property hyperlinks on Telegram (known limitation).

---

## Case 1 - Investment flow + financing hand-off

An investor is browsing the website, looking to buy an apartment with 7% yield in the region. The real estate agent helps the customer browse properties, and the mortgage agent answers questions about fees (ITBI) for the listed properties.

[▶ Watch video](videos/case_01.mp4)

## Case 2 - Hand-off + booking

A customer is browsing the website, looking to buy a house. The real estate agent offers the only property available in the city and warns the customer that it's above their provided price range. The mortgage agent helps with financing advice, and the real estate agent books the visit for the customer.

[▶ Watch video](videos/case_02.mp4)

## Case 3 - Regional data (RAG)

The customer is browsing the website but doesn't yet know exactly where to buy/rent. The real estate agent helps the customer browse properties based on the provided geo data.

[▶ Watch video](videos/case_03.mov)

## Case 4 - Investment flow via Telegram

An investor is interacting with the Telegram bot, looking to buy an apartment with 7% yield in the region. The real estate agent helps the customer browse properties, and the mortgage agent answers questions about fees (ITBI) for the listed properties.

[▶ Watch video](videos/case_04.mp4)

## Case 5 - Hand-off + booking + agenda via Telegram

A customer is interacting with the Telegram bot, looking to buy a house. The real estate agent can't find any property with the desired description and offers an apartment instead. The mortgage agent helps with financing advice, and the real estate agent books the visit for the customer. The broker's agenda is updated with the scheduled appointment.

[▶ Watch video](videos/case_05.mp4)

## Case 6 - Inactivity follow-up + price drop

A customer is interacting with the Telegram bot, looking to buy an apartment. The real estate agent suggests an option to the customer but gets no response. After 2 minutes, the follow-up agent sends a message nudging for a response. Meanwhile, the property's price drops in the CRM (via `make drop-price PROPERTY_ID=25 PRICE=370000`), so the follow-up agent sends another notification displaying the new price.

[▶ Watch video](videos/case_06.mp4)

## Case 7 - Broker & admin dashboards

This video demonstrates the Real Estate Agency dashboard, which has the broker's visit agenda (with past and upcoming bookings) as well as general data about the company. It also tracks the most and least sought-after properties, and lead categorization. There's also an Admin panel to follow up on LLM interactions and expenditures.

[▶ Watch video](videos/case_07.mov)

## Case 8 - Prompt injection

A customer is interacting with the Telegram bot, trying to get access to the LLM's system prompt. The agent has prompt safeguards and correctly blocks the attempt. The malicious attempt can be seen logged in the Admin panel.

[▶ Watch video](videos/case_08.mov)
