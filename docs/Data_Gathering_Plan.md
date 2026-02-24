# Data Gathering Plan for Enrollment Forecasting (FERPA Compliant)

To build a highly accurate **Cohort-Based Flow Model** while strictly adhering to FERPA regulations, we will use **Aggregated Counts** instead of student-level data. We do *not* need names or IDs.

## 1. Admissions Data (The "Pipeline")
**Purpose**: To determine the size of the incoming cohort by major.

*   **Request**: "Aggregated Count of Confirmed Deposits for Fall [Next Academic Year]"
*   **Format**: Excel / CSV
*   **Required Fields**:
    *   `Major` (e.g., "Accessory Design")
    *   `Student Type` (Freshman vs. Transfer)
    *   `Count of Confirmed Deposits` (e.g., 45)
    *   `Entry Term` (e.g., Fall 2026)

## 2. Current Enrollment Data (The "Feeder")
**Purpose**: To know the volume of students currently in the pipeline to predict their next step.

*   **Request**: "Aggregated Enrollment Counts for [Current Term]"
*   **Format**: Excel / CSV
*   **Required Fields**:
    *   `Course Code` (e.g., FOUN 110)
    *   `Major` (e.g., "Accessory Design")
    *   `Student Level` (Freshman, Sophomore, etc.)
    *   `Count of Enrolled Students` (e.g., 120)

## 3. Historical Data (The "Behavior")
**Purpose**: To calculate "Melt Rates" and "Off-Sequence Demand" based on historical trends.

*   **Request**: "Historical Course Enrollment Summaries (Last 3-5 Years)"
*   **Format**: Excel / CSV
*   **Required Fields**:
    *   `Term` (e.g., Fall 2023)
    *   `Course Code`
    *   `Major` (Optional, but highly recommended for accuracy)
    *   `Total Enrollment Count`
    *   **`Total Waitlist Count`** (Critical for "True Demand")
    *   `Section Count` (Number of sections offered)

## 4. Curriculum Logic (The "Rules")
**Purpose**: To map the path of a student group.

*   **Action**: Create a clean "Sequence Map" (CSV).
*   **Structure**:
    *   `Major`
    *   `Course Code`
    *   `Sequence Order` (1, 2, 3...)
    *   `Standard Term` (Fall, Winter, Spring)

## Summary Checklist
- [ ] **Admissions Report**: Total counts by Major and Student Type.
- [ ] **Current Enrollment**: Total counts by Course and Major.
- [ ] **Historical Data**: Total counts by Term, Course, and Major (with waitlists).
- [ ] **Sequence Map**: Course progression list.
