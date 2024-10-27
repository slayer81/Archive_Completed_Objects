I found that I regularly forgot to clean-up items, such as Linux ISOs and Docker images that I downloaded using Transmission, and since these are downloaded to my super fast, yet small, NVMe disk, I wanted a way to automatically move completed items to a larger archive disk.

This project allowed me to explore a variety of concepts from the ["Automate the Boring Stuff With Python"](https://automatetheboringstuff.com/2e/chapter0/) series by Al Sweigart. I recommend it to other arm-chair Python warriors like myself.

**Platform**: macOS 15.0 Sequoia  
**Execution**: LaunchControl

Instead of using cron, I use LaunchControl for scheduling various processes. Unfortunately, it doesn't always like to extract parameters from my ~/.bash_profile, so I added a step to "source" my profile, so that I don't have to hard code values in the script, and also allow me to change archive destination once, and have it propagate as needed. (because I'm lazy)

The overall flow of this is:

  -  Load profile
  -  Poll Transmission API for active objects
  -  Get object list from Transmission download location
  -  De-dupe the two, leaving just items to archive
  -  Classify each item in the actioning list (this wasn't really needed, but I wanted to make this usable in the future)
    -  For each actionable item:
      - symbolic link: unlink it
      - files / directories:
        - first checking if it already exists (to account for any previous uncompleted events).
        - If a version exists, check the quality (total object size).
        - If the active object is larger, overwrite.
        - If not, move to the "Graveyard" for verification.
        - Otherwise, move to the Archive path
      - Log any failures
