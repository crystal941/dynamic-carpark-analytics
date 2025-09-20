
#!/usr/bin/env Rscript
rmarkdown::render("dashboard.Rmd", output_file = "index.html", output_dir = "output")
cat("[OK] Rendered output/index.html\n")
