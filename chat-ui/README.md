# Nova Chat

Create a modern, polished ChatGPT-style chatbot application UI. This is a frontend/UI-only project for now: do not build any backend, database, authentication, API integrations, or real AI functionality. Use realistic mock data throughout.

Core Goal

Add authentication

Build an interactive conversational AI interface where users can:

Create and manage multiple chat sessions

Switch between previous conversations

Start a new chat

Send messages and see mock assistant responses

Experience a simulated streaming response

Upload files directly within a chat

Configure global AI/user preferences from one Settings area

Have a highly polished, responsive experience similar in usability to ChatGPT

Layout

1. Left Sidebar

Create a collapsible sidebar containing:

Top section

App logo/name: "Nova AI"

"New Chat" button with prominent icon

Search conversations input

Conversation history
Group chats by:

Today

Yesterday

Previous 7 Days

Older

Each chat item should have:

Conversation title

Optional small icon

Hover state

Active state

More menu (...) with:

Rename

Delete

Archive

Use realistic mock conversations.

Bottom section

User profile/avatar

User name and email

Settings

Theme toggle

Help / feedback

The sidebar should collapse into an icon-only rail on desktop and become a drawer on mobile.

2. Main Chat Area

Create a clean, spacious chat interface.

Top navigation

Current conversation title

Dropdown/chevron

Optional model selector such as:

Nova Fast

Nova Pro

Share button

More menu

Empty/New Chat State

When starting a new conversation, show:

Large friendly greeting

"How can I help you today?"

4–6 interactive suggestion cards, for example:

Summarize a document

Write something

Analyze data

Brainstorm ideas

Explain a concept

Help me plan something

Clicking a suggestion should populate/send a mock prompt.

3. Chat Messages

Create a polished conversation UI supporting:

User messages

Right-aligned or visually differentiated

Avatar

Message text

Timestamp

Attached file cards when applicable

Assistant messages

Left-aligned

AI avatar/logo

Markdown-like formatting

Headings

Lists

Code blocks

Inline code

Tables where appropriate

Copy button

Regenerate button

Thumbs up/down feedback

More actions

Use realistic mock conversations containing multiple turns.

4. Streaming Response Simulation

The UI must visually support a streaming assistant response even though there is no backend.

When the user sends a message:

Immediately add the user message.

Show an assistant typing/loading indicator.

Simulate the assistant response appearing progressively, character-by-character or word-by-word.

Show a subtle "Stop generating" button while streaming.

Allow the user to stop the mock stream.

After completion, show the normal assistant message actions.

Create a reusable mock streaming mechanism so this behavior can easily be connected to a real API later.

Do not implement a real AI API.

5. Chat Composer

At the bottom of the chat, create a premium ChatGPT-style message composer.

Include:

Multiline text input

Attach/upload button

File picker UI using mock/local state only

Microphone icon

Send button

Optional model selector

The composer should:

Expand vertically as the user types

Send with Enter

Create a new line with Shift + Enter

Disable send when empty

Show loading/streaming state

Have polished focus, hover and disabled states

6. File Upload UI

Support the UI for uploading files without implementing backend storage.

When the user selects a file:

Display it as an attachment chip/card inside the composer

Show:

Filename

File type

File size

Remove button

Support multiple mock attachments

Simulate upload progress

Show completed/uploading/error states

Include realistic examples such as:

PDF

DOCX

XLSX

CSV

TXT

Images

The file data does not need to leave the browser.

7. Global Settings

Create one comprehensive Settings screen/modal accessible from the sidebar.

Organize settings into sections:

General

Theme: Light / Dark / System

Language

Compact mode

Animations toggle

AI Preferences

"What should the AI know about you?"

"How would you like the AI to respond?"

Response style:

Concise

Balanced

Detailed

Custom

Preferred tone:

Professional

Friendly

Casual

Technical

Personalization
Add editable text areas for:

About me

My preferences

Instructions for the AI

Include helper text explaining that these preferences will apply globally to future conversations.

Chat

Enter to send

Show timestamps

Auto-scroll

Save chat history

Default model

Privacy
Use mock toggles for:

Chat history

Improve AI

Remember preferences

Include a clear "Save Changes" button and success toast.

8. Interactive Behaviors

Make the UI feel like a real application.

Implement frontend-only interactions for:

New chat

Switching chats

Renaming chats

Deleting chats

Searching chats

Opening/closing sidebar

Settings

Theme switching

Sending messages

Mock streaming

Stop generation

Regenerate response

Copy message

Like/dislike feedback

File attachment/removal

Composer resizing

Suggestion cards

Toast notifications

Dropdowns and menus

Keyboard shortcuts where appropriate

Use local React state/mock data. No backend is required.

9. Responsive Design

The application must work beautifully on:

Desktop

Laptop

Tablet

Mobile

On mobile:

Sidebar becomes a slide-out drawer

Chat takes the full viewport

Composer remains accessible

Settings becomes a full-screen modal/page

Message bubbles and file cards adapt to smaller widths

10. Visual Design

Use a premium, minimal AI-product aesthetic inspired by ChatGPT, but do not copy ChatGPT branding.

Design characteristics:

Clean whitespace

Neutral background

Subtle borders

Rounded cards

Soft shadows

Excellent typography

Smooth transitions

Modern icons

Accessible contrast

Light and dark themes

Use a restrained accent color for primary actions.

Avoid excessive gradients, unnecessary decoration, or a generic dashboard appearance. The product should feel like a focused, production-quality AI chat application.

11. Mock Data

Create realistic mock data for:

10–15 conversations

Different conversation titles

Multiple messages per conversation

Different assistant responses

Attached files

User profile

Global preferences

Streaming response

Example conversation titles:

"Q3 Marketing Strategy"

"Explain React Server Components"

"Product Launch Ideas"

"Analyze Sales Report"

"Travel Planning"

"Python Debugging"

"Meeting Notes Summary"

Persist UI state using local storage where useful, but do not create a backend.

12. Technical Expectations

Use a clean component architecture with reusable components such as:

Sidebar

ChatList

ChatHeader

ChatMessages

Message

MessageActions

ChatComposer

FileAttachment

StreamingMessage

SuggestionCards

Settings

SettingsSection

ModelSelector

Toast

ConfirmDialog

Keep the mock data and mock streaming logic separated from UI components so a real backend/API can be connected later with minimal changes.

Important Constraints

DO:

Build the complete UI

Make interactions functional using mock/local state

Make streaming responses visually realistic

Make file upload interactions functional on the frontend

Make the application responsive

Use realistic mock data

Focus heavily on UX polish

DO NOT:

Build a backend

Add a database

Connect to OpenAI or any other AI API

Create real chat persistence on a server

Implement server-side file storage

Require API keys

The final result should look and behave like a high-quality production AI chatbot frontend, while all data and AI behavior remain mocked locally.

## Development

You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
npm i
npm run dev
```
