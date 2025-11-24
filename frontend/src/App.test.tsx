import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';
import App from './App';

jest.mock('axios', () => {
  const post = jest.fn();
  return {
    __esModule: true,
    default: { post },
    post,
  };
});

const mockedAxios = axios as unknown as { post: jest.Mock };

beforeAll(() => {
  // Prevent errors from useRef scroll calls in JSDOM.
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
});

afterEach(() => {
  jest.clearAllMocks();
});

test('renders header and disables send when input is empty', () => {
  render(<App />);

  expect(screen.getByText(/technical support assistant/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /send/i })).toBeDisabled();
});

test('sends user message and displays assistant reply', async () => {
  mockedAxios.post.mockResolvedValueOnce({
    data: { answer: 'Here to help!', context_used: [] },
  });

  render(<App />);

  fireEvent.change(screen.getByPlaceholderText(/technical issue/i), {
    target: { value: 'Hello?' },
  });
  fireEvent.click(screen.getByRole('button', { name: /send/i }));

  expect(mockedAxios.post).toHaveBeenCalledWith(
    expect.stringContaining('/chat/ask'),
    {
      content: 'Hello?',
      conversation_history: [],
    }
  );

  await waitFor(() =>
    expect(screen.getByText(/here to help/i)).toBeInTheDocument()
  );
});
