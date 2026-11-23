import type { RoadmapCareerId } from './roadmapData'

export type ResourceKind = 'pdf' | 'book' | 'course'
export type Level = 'Beginner' | 'Intermediate' | 'Advanced'

export type LearnResource = {
  title: string
  author: string
  kind: ResourceKind
  level: Level
  why: string
  url: string
  starter?: boolean // "start here" pick
}

const openLibrary = (title: string) => `https://openlibrary.org/search?q=${encodeURIComponent(title)}`

// "pdf" = free and legally published by the author/publisher (PDF or full online book).
export const learnResources: Record<RoadmapCareerId, LearnResource[]> = {
  software: [
    { title: 'Eloquent JavaScript', author: 'Marijn Haverbeke', kind: 'pdf', level: 'Beginner', why: 'A friendly, project-based introduction to programming with JavaScript.', url: 'https://eloquentjavascript.net/', starter: true },
    { title: 'Think Python', author: 'Allen B. Downey', kind: 'pdf', level: 'Beginner', why: 'Learn to think like a programmer using Python.', url: 'https://greenteapress.com/wp/think-python-2e/' },
    { title: 'Pro Git', author: 'Scott Chacon & Ben Straub', kind: 'pdf', level: 'Beginner', why: 'Everything about Git and GitHub, free from the official Git site.', url: 'https://git-scm.com/book/en/v2' },
    { title: "You Don't Know JS Yet", author: 'Kyle Simpson', kind: 'pdf', level: 'Intermediate', why: 'Deep understanding of how JavaScript really works.', url: 'https://github.com/getify/You-Dont-Know-JS' },
    { title: 'Clean Code', author: 'Robert C. Martin', kind: 'book', level: 'Intermediate', why: 'Write code that is easy to read and maintain.', url: openLibrary('Clean Code Robert Martin') },
    { title: 'The Pragmatic Programmer', author: 'David Thomas & Andrew Hunt', kind: 'book', level: 'Intermediate', why: 'Habits and mindset of effective developers.', url: openLibrary('The Pragmatic Programmer') },
    { title: 'MDN: Learn web development', author: 'Mozilla', kind: 'course', level: 'Beginner', why: 'HTML, CSS and JavaScript from zero.', url: 'https://developer.mozilla.org/en-US/docs/Learn_web_development' },
    { title: 'React: Learn', author: 'React team', kind: 'course', level: 'Beginner', why: 'Official React tutorial with interactive examples.', url: 'https://react.dev/learn' },
    { title: 'CS50x', author: 'Harvard University', kind: 'course', level: 'Beginner', why: 'The famous free intro to computer science.', url: 'https://cs50.harvard.edu/x/' },
  ],
  data: [
    { title: 'Python for Data Analysis (3rd ed.)', author: 'Wes McKinney', kind: 'pdf', level: 'Beginner', why: 'Written by the creator of pandas; free online edition.', url: 'https://wesmckinney.com/book/', starter: true },
    { title: 'OpenIntro Statistics', author: 'Diez, Çetinkaya-Rundel & Barr', kind: 'pdf', level: 'Beginner', why: 'Clear, free statistics textbook with exercises.', url: 'https://www.openintro.org/book/os/' },
    { title: 'Think Stats', author: 'Allen B. Downey', kind: 'pdf', level: 'Beginner', why: 'Statistics explained through Python code.', url: 'https://greenteapress.com/wp/think-stats-3e/' },
    { title: 'R for Data Science (2e)', author: 'Hadley Wickham et al.', kind: 'pdf', level: 'Intermediate', why: 'Data cleaning and visualization with R.', url: 'https://r4ds.hadley.nz/' },
    { title: 'Storytelling with Data', author: 'Cole Nussbaumer Knaflic', kind: 'book', level: 'Beginner', why: 'Make charts that people actually understand.', url: openLibrary('Storytelling with Data') },
    { title: 'Naked Statistics', author: 'Charles Wheelan', kind: 'book', level: 'Beginner', why: 'Fun, non-scary explanation of statistics ideas.', url: openLibrary('Naked Statistics Wheelan') },
    { title: 'SQLBolt', author: 'SQLBolt', kind: 'course', level: 'Beginner', why: 'Interactive SQL lessons in the browser.', url: 'https://sqlbolt.com/' },
    { title: 'Kaggle Learn: Pandas', author: 'Kaggle', kind: 'course', level: 'Beginner', why: 'Short hands-on pandas lessons.', url: 'https://www.kaggle.com/learn/pandas' },
  ],
  design: [
    { title: 'Practical Typography', author: 'Matthew Butterick', kind: 'pdf', level: 'Beginner', why: 'Free online book on making text look good.', url: 'https://practicaltypography.com/', starter: true },
    { title: 'Laws of UX', author: 'Jon Yablonski', kind: 'pdf', level: 'Beginner', why: 'Free guide to the psychology behind good design.', url: 'https://lawsofux.com/' },
    { title: 'The Design of Everyday Things', author: 'Don Norman', kind: 'book', level: 'Beginner', why: 'The classic on why some designs are easy and others confusing.', url: openLibrary('The Design of Everyday Things') },
    { title: "Don't Make Me Think", author: 'Steve Krug', kind: 'book', level: 'Beginner', why: 'Short, practical book on web usability.', url: openLibrary("Don't Make Me Think Krug") },
    { title: 'Refactoring UI', author: 'Adam Wathan & Steve Schoger', kind: 'book', level: 'Intermediate', why: 'Practical tips to make interfaces look polished.', url: 'https://www.refactoringui.com/' },
    { title: 'Figma Learn', author: 'Figma', kind: 'course', level: 'Beginner', why: 'Official Figma tutorials.', url: 'https://help.figma.com/hc/en-us' },
    { title: 'Google UX Design Certificate', author: 'Google / Coursera', kind: 'course', level: 'Beginner', why: 'Structured UX course (free to audit).', url: 'https://www.coursera.org/professional-certificates/google-ux-design' },
  ],
  ai: [
    { title: 'Mathematics for Machine Learning', author: 'Deisenroth, Faisal & Ong', kind: 'pdf', level: 'Beginner', why: 'All the math you need for ML, free PDF from the authors.', url: 'https://mml-book.github.io/', starter: true },
    { title: 'An Introduction to Statistical Learning', author: 'James, Witten, Hastie & Tibshirani', kind: 'pdf', level: 'Beginner', why: 'The best first ML textbook; free PDF with Python labs.', url: 'https://www.statlearning.com/' },
    { title: 'Dive into Deep Learning', author: 'Zhang, Lipton, Li & Smola', kind: 'pdf', level: 'Intermediate', why: 'Interactive deep learning book with runnable code.', url: 'https://d2l.ai/' },
    { title: 'Deep Learning', author: 'Goodfellow, Bengio & Courville', kind: 'pdf', level: 'Advanced', why: 'The reference deep learning textbook, free online.', url: 'https://www.deeplearningbook.org/' },
    { title: 'Hands-On Machine Learning', author: 'Aurélien Géron', kind: 'book', level: 'Intermediate', why: 'Practical scikit-learn and deep learning projects.', url: openLibrary('Hands-On Machine Learning Geron') },
    { title: 'Google ML Crash Course', author: 'Google', kind: 'course', level: 'Beginner', why: 'Fast, free intro to ML concepts.', url: 'https://developers.google.com/machine-learning/crash-course' },
    { title: 'Practical Deep Learning for Coders', author: 'fast.ai', kind: 'course', level: 'Intermediate', why: 'Build real models from lesson one.', url: 'https://course.fast.ai/' },
  ],
  product: [
    { title: 'Shape Up', author: 'Ryan Singer (Basecamp)', kind: 'pdf', level: 'Beginner', why: 'How teams plan and ship product work; free online and PDF.', url: 'https://basecamp.com/shapeup', starter: true },
    { title: 'Inspired', author: 'Marty Cagan', kind: 'book', level: 'Beginner', why: 'The go-to book on how great product teams work.', url: openLibrary('Inspired Marty Cagan') },
    { title: 'The Mom Test', author: 'Rob Fitzpatrick', kind: 'book', level: 'Beginner', why: 'Learn to talk to users without getting misleading answers.', url: openLibrary('The Mom Test') },
    { title: 'The Lean Startup', author: 'Eric Ries', kind: 'book', level: 'Beginner', why: 'Build, measure, learn — testing ideas quickly.', url: openLibrary('The Lean Startup') },
    { title: 'Hooked', author: 'Nir Eyal', kind: 'book', level: 'Intermediate', why: 'How products build user habits.', url: openLibrary('Hooked Nir Eyal') },
    { title: 'Atlassian: Product management guide', author: 'Atlassian', kind: 'course', level: 'Beginner', why: 'Free guide to discovery, roadmaps and prioritization.', url: 'https://www.atlassian.com/agile/product-management' },
  ],
}
