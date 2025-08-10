# Don't run 
udmodel <- udpipe_download_model(language = "russian")
save(udmodel, file = "udmodel_ru.RData")
load("udmodel_ru.RData")

udmodel_1 <- udpipe_load_model(file = udmodel$file_model)

health_texts_ru <- health_texts %>% filter(lang == "ru")
# takes a lot of time
set.seed(1312)
txt_df_raw <- udpipe_annotate(udmodel_1, 
                              health_texts_ru$text, 
                              doc_id = health_texts_ru$doc_id, 
                              parser = "none",
                              trace = TRUE) %>%
  as_tibble() %>%
  select(-xpos, -feats, -head_token_id, -dep_rel, -misc, -deps) %>%
  mutate(word = str_to_lower(lemma))

save(txt_df_raw, file = "annotated_df.RData")
load("annotated_df.RData")
ru_ids <- 
  health_texts %>% 
  filter(lang == "ru") %>% 
  pull(doc_id)

txt_ru <-
  txt_df_raw %>% 
  filter(doc_id %in% ru_ids)

txt_tidy <-
  txt_ru %>%
  # This mutate() replaces all non-NAVs with xxx
  mutate(word = replace(word, !(upos %in% c("NOUN", "ADJ", "VERB")), "xxx")) %>%
  # This mutate() affixes pos-tags to words
  mutate(word = paste0(word, "_", str_to_lower(upos))) %>%
  separate(word, sep = "_(?=[^_]+$)", 
           c(NA, "real_upos"), remove = FALSE) %>%
  mutate(upos = str_to_upper(real_upos)) %>%
  select(-real_upos)

## topics modelling

dtf_df <- 
  txt_tidy %>% 
  filter(upos %in% c("NOUN", "ADJ", "VERB")) %>%
  filter(!(str_detect(word, "xxx_")))
dtf <- 
  document_term_frequencies(dtf_df, 
                            document = c("doc_id"), 
                            term = "word")
dtm <- document_term_matrix(x = dtf)
dtm_clean <- dtm_remove_lowfreq(dtm, minfreq = 2)

dfm_q <- quanteda::as.dfm(dtm_clean)

out <- convert(dfm_q, to = "stm")
doc_ids <- docnames(dfm_q)

stm_model <- stm(
  documents = out$documents,
  vocab = out$vocab,
  K = 4,
  seed = 1312
)
rownames(stm_model$theta) <- doc_ids
save(stm_model, file = "topics.RData")
load("topics.RData")
betas <- 
  tidy(stm_model) %>%
  rename(word = term)
betas_20 <- 
  betas %>%
  group_by(topic) %>%
  top_n(20, beta) %>%
  ungroup() %>% 
  arrange(topic, desc(beta)) %>%
  mutate(topic = paste0("Topic ", topic))

fig_topics <- 
  betas_20 %>% 
  mutate(word = reorder_within(word, beta, topic)) %>%
  ggplot(aes(fct_reorder(word, beta), beta, fill = as.factor(topic))) +
  geom_col(alpha = 0.8, show.legend = FALSE) +
  facet_wrap(~ topic, scales = "free_y") +
  coord_flip() +
  scale_x_reordered() +
  labs(x = NULL, y = expression(beta),
       title = "Highest word probs for each topic",
       subtitle = "Different words are associated with different topics")
fig_topics
ggsave(
  filename = "img/fig_topics.pdf",
  plot = fig_topics,
  width = 8,
  height = 6,
  device = cairo_pdf    
)
stm_model$theta

topic_fractions <-
  stm_model$theta %>% 
  as.data.frame() %>%
  rename(t1 = V1, 
         t2 = V2, 
         t3 = V3, 
         t4 = V4) %>% 
  rownames_to_column(var = "doc_id") %>%
  as_tibble()
topic_fractions


health_texts_smaller_ru <- 
  health_texts_smaller_ru %>% 
  left_join(topic_fractions, by = "doc_id")

df_long <- health_texts_smaller_ru %>%
  pivot_longer(
    cols = c("t1", "t2", "t3", "t4"),
    names_to = "topic",
    values_to = "proportion"
  )

ggplot(df_long, 
       aes(x = published_time, y = proportion, 
           color = topic)) +
  geom_smooth(se = FALSE, 
              span = 0.4) + 
  labs(
    title = "Topic Proportions Over Time",
    x = "Date",
    y = "Topic Proportion",
    color = "Topic"
  ) +
  theme_minimal()


df_roll <- df_long %>%
  arrange(topic, published_time) %>%
  group_by(topic) %>%
  mutate(topic_roll_mean = zoo::rollmean(proportion, 
                                         k = 7, fill = NA, align = "right")) %>%
  ungroup()


fig_sliding_topics <- 
  df_roll %>% 
  filter(year < 2022) %>% 
  mutate(published_time = as.Date(published_time)) %>%
  ggplot(aes(x = published_time, color = topic)) +
  geom_point(aes(y = proportion), alpha = 0.3) +
  geom_line(aes(y = topic_roll_mean), size = 1) +
  labs(
    title = "Topic Proportions with 7-Doc Rolling Average",
    x = "Date",
    y = "Proportion",
    color = "Topic"
  ) +
  theme_minimal()
fig_sliding_topics

txt_tidy_nav <-
  txt_tidy %>% 
  filter(upos %in% c("NOUN", "ADJ", "VERB")) %>%
  filter(!(str_detect(word, "xxx_")))

txt_tidy_nav <- 
  txt_tidy_nav %>% 
  left_join(health_texts %>% 
              select(doc_id, published_time), by = "doc_id") %>% 
  mutate(published_time = as.Date(published_time), 
         year = year(published_time), 
         month = month(published_time), 
         year_month = format(published_time, "%Y-%m"),
         quarter = quarter(as.Date(paste0(year_month, "-01"))), 
         year_quarter = str_c(year, "Q", quarter, sep = "_"))

news_words <- 
  txt_tidy_nav %>%
  count(word, year_quarter, sort = TRUE)

total_words <- 
  news_words %>% 
  group_by(year_quarter) %>% 
  summarize(total = sum(n))

news_words <- 
  left_join(news_words, 
            total_words)

news_words

freq_by_rank <- 
  news_words %>% 
  group_by(year_quarter) %>% 
  mutate(rank = row_number(), 
         term_frequency = n/total) %>%
  ungroup()

news_tf_idf <- 
  news_words %>%
  filter(n > 10) %>%
  bind_tf_idf(word, year_quarter, n)

plot_news <- 
  news_tf_idf %>%
  group_by(year_quarter) %>% 
  slice_max(tf_idf, n = 15) %>%
  ungroup() %>%
  mutate(word = fct_reorder(word, tf_idf))

write_csv(plot_news, file = "out/tf_idf_quarters.csv")

ggplot(plot_news, aes(tf_idf, word)) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~year_month, ncol = 15, scales = "free") +
  labs(x = "tf-idf", y = NULL)
