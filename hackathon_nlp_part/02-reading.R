# -------------------------------------------------------------------
# Corpus import
# -------------------------------------------------------------------
theme_set(theme_minimal())
health_texts <- # this one is to go to the surface branch
  readtext("data/corpus/*", text_field = "article", docid_field = "post_id") %>%
  mutate(text = if_else(is.na(text), title, text)) %>%
  filter(!is.na(text))
health_texts$text %>% is.na() %>% sum()

write_csv(health_texts %>% 
            select(doc_id, text, lang) %>% 
            filter(lang == "ru"), 
          file = "python_parts/texts.csv")

health_texts %>% filter(is.na(text)) %>% head() %>% View()
health_corpus <- # this one is to go to the topic branch
  corpus(health_texts, 
         docid_field = "doc_id", text_field = "text")

health_tokens <- 
  unnest_tokens(health_texts %>% 
                  select(-lang, -url, -likes:-theme2, -pos_comment_count:-tg_neg_reaction), 
                output = "word", 
                input = "text", 
                token = "words", 
                strip_punct = TRUE) %>%
  rename(token = word)

lex <- hash_sentiment_afinn_ru


health_sent <- 
  health_tokens %>%
  inner_join(lex)


health_sent_by_doc <-
  health_sent %>%
  group_by(doc_id, title) %>%
  summarise(sum = sum(score))

library(lubridate)
health_texts_smaller_ru <-
  health_texts %>%
  select(doc_id:title, region) %>%
  select(-url, -text) %>%
  left_join(health_sent_by_doc) %>%
  filter(lang == "ru") %>%
  mutate(published_time = parse_datetime(published_time)) %>%
  mutate(year_month = format(published_time, "%Y-%m"), 
         year = year(published_time)) %>%
  mutate(sum = if_else(is.na(sum), 0, sum))

health_texts_smaller_ru %>% 
  filter(year < 2022) %>%
  group_by(year_month) %>%
  summarise(mean = mean(sum, na.rm = TRUE), n = n()) %>%
  ungroup() %>%
  ggplot(aes(x = year_month, y = mean)) +
  geom_line() +
  geom_point()

library(zoo)
library(slider)
health_texts_smaller_ru <-
  health_texts_smaller_ru %>% 
  arrange(published_time) %>%
  mutate(
    emotions_roll7 = rollmean(sum, k = 7, fill = NA, align = "right"),
    emotions_roll14 = rollmean(sum, k = 14, fill = NA, align = "right")
  )

fig_sliding_emo <- 
  health_texts_smaller_ru %>% 
  filter(year < 2022) %>% 
  mutate(published_time = as.Date(published_time)) %>%
  ggplot(aes(x = published_time)) +
  geom_point(aes(y = sum), color = "grey70", alpha = 0.7, size = 0.6) +
  geom_line(aes(y = emotions_roll7), color = "tomato", size = 0.5) +
  geom_line(aes(y = emotions_roll14), color = "blue", size = 1) +
  labs(title = "Sliding Mean Over Time",
       y = NULL, x = NULL) + 
  scale_x_date(date_breaks = "1 year") + 
  theme_minimal(base_size = 16)

# Save as high-resolution PNG
ggsave(
  filename = "img/fig_sliding_emo.png",
  plot = fig_sliding_emo,
  width = 8,           
  height = 6,          
  dpi = 300,           
  bg = "white"         
)

# Save as vector PDF for infinite scaling
ggsave(
  filename = "img/fig_sliding_emo.pdf",
  plot = fig_sliding_emo,
  width = 8,
  height = 6,
  device = cairo_pdf    
)



health_texts_smaller_ru
