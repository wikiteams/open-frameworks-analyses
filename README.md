open-frameworks-analyses
========================

#### Introduction

Issues survival and local regression analyses of frameworks on GitHub

### License

The MIT License (MIT)

Copyright (c) 2014 WikiTeams.pl

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Description

In this project we take data from openhub to create a list of frameworks which have their open source available on GitHub portal, next we make analyses of their popularity together with issues survival methods and offline assessment of code.

#### FAQ

**Q:** Who can add a project to OpenHub ?

**A:** Everyone – project’s contributors and owners.

### OpenHub

We took list of open source frameworks from the OpenHub and filtered those which don't have a source code on the GitHub. This OpenHub dataset contains also some other useful information, e.g. rating from users, reports on activity et cetera.

### LineUp

It is discussable which property is a best for rating the popularity of a GitHub repository. Apart from number of stars, external ratings e.g. number of votes on GitHub and number of visits (as given by network_count from GitHub API) maybe be usefull to combine all features together.

### Yasca

Yasca is a 3rd party code quality analyzer. We will try to analyze the code regarding their offline characteristics on programming code. Most of major languages are supported. 

### Issues survival

Issues survival will need list of issues for repositories included in the main dataset. List of issues will need to have below attributes: date of issue open, date of issue closure (naturally can be 'NA'), repository name (for aggregating). Labels are also required but they can be in seperate file.
